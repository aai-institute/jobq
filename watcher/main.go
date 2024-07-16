package main

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"os"
	"strings"
	"time"

	"github.com/nikoksr/notify"
	log "github.com/sirupsen/logrus"
	batchv1 "k8s.io/api/batch/v1"
	corev1 "k8s.io/api/core/v1"
	v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	kubeinformers "k8s.io/client-go/informers"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/tools/clientcmd"

	httpnotify "github.com/nikoksr/notify/service/http"
	"github.com/nikoksr/notify/service/slack"
)

var (
	config, _    = clientcmd.BuildConfigFromFlags("", os.Getenv("KUBECONFIG"))
	clientset, _ = kubernetes.NewForConfig(config)
)

// Check if a job has transitioned from being suspended to running
func wasUnsuspended(oldJob *batchv1.Job, newJob *batchv1.Job) bool {
	if oldJob.Spec.Suspend == nil || newJob.Spec.Suspend == nil {
		return false
	}
	return *oldJob.Spec.Suspend && !*newJob.Spec.Suspend
}

// Check if a Job is completed
func isCompleted(job *batchv1.Job) bool {
	return job.Status.CompletionTime != nil
}

// Check if a Job contains any failed Pods
func hasFailedPods(job *batchv1.Job) bool {
	return job.Status.Failed > 0
}

func getNotifierKey(obj *batchv1.Job) string {
	notifier := obj.Annotations["x-jobby.io/notify-channel"]
	return notifier
}

type KueueMetadata struct {
	QueueName     string
	PriorityClass string
}

// Extract metadata from a Kueue Job
func getKueueMetadata(job *batchv1.Job) (KueueMetadata, error) {
	queueName := job.Labels["kueue.x-k8s.io/queue-name"]
	priorityClass := job.Labels["kueue.x-k8s.io/priority-class"]

	if queueName == "" {
		return KueueMetadata{}, fmt.Errorf("not a Kueue job: %s", job.Name)
	}

	return KueueMetadata{queueName, priorityClass}, nil
}

func getNotifier(key string, jobAnnotations map[string]string) notify.Notifier {
	switch key {
	case "slack":
		log.Debug("Using Slack notifier")
		service := slack.New(os.Getenv("WATCHER_SLACK_API_TOKEN"))
		receivers := jobAnnotations["x-jobby.io/slack-channel-ids"]
		log.Debug("Slack notifier channel IDs: ", receivers)

		if receivers == "" {
			return nil
		}
		service.AddReceivers(strings.Split(receivers, ",")...)
		return service

	case "webhook":
		log.Debug("Using Webhook notifier")
		service := httpnotify.New()
		receivers := jobAnnotations["x-jobby.io/webhook-urls"]
		log.Debug("Webhook notifier URLs: ", receivers)

		if receivers == "" {
			return nil
		}
		service.AddReceiversURLs(strings.Split(receivers, ",")...)
		return service
	}
	return nil
}

func handleUpdate(obj interface{}, newObj interface{}) {
	job := obj.(*batchv1.Job)
	newJob := newObj.(*batchv1.Job)

	notifierKey := getNotifierKey(job)
	notifier := getNotifier(notifierKey, newJob.Annotations)
	if notifier == nil {
		log.Warnf("Could not determine notifier, %+v", job.Annotations)
		return
	}
	useMarkdown := notifierKey == "slack"

	if wasUnsuspended(job, newJob) {
		var subject, body string
		if useMarkdown {
			subject = fmt.Sprintf(":runner: *+++ Job `%s` started running +++*", job.Name)

			builder := new(strings.Builder)
			builder.WriteString("\n")

			kueueMetadata, err := getKueueMetadata(job)
			if err == nil {
				fmt.Fprintf(builder, "*Kueue metadata*\n\n- Cluster queue: `%s`\n- Priority class: `%s`\n", kueueMetadata.QueueName, kueueMetadata.PriorityClass)
			}

			builder.WriteString(formatJob(job, true))
			body = builder.String()
		} else {
			subject = "Job started running"
			body = formatJob(job, true)
		}

		notifier.Send(context.Background(), subject, body)
	}

	if hasFailedPods(newJob) {
		var subject, body string
		if useMarkdown {
			subject = fmt.Sprintf(":warning: *+++ Job `%s` has failed pods +++*", job.Name)

			pods, _ := getManagedPods(job)

			buf := new(strings.Builder)
			buf.WriteString("\n")

			buf.WriteString("*Failed Pods*\n\n")

			for _, pod := range pods {
				if pod.Status.Phase != corev1.PodFailed {
					continue
				}
				logs, _ := getPodLogs(pod)
				fmt.Fprintf(buf, "Pod `%s`\n```\n%s\n```\n\n", pod.Name, logs)

			}
			body = buf.String()
		} else {
			subject = "Job completed"
			body = formatJob(job, false)
		}

		notifier.Send(context.Background(), subject, body)
	}

	if !isCompleted(job) && isCompleted(newJob) {
		var subject, body string
		if useMarkdown {
			subject = fmt.Sprintf(":white_check_mark: *+++ Job `%s` completed +++*", job.Name)
			outputs, _ := collectJobOutputs(job)

			buf := new(strings.Builder)
			buf.WriteString("\n")
			for podName, logs := range outputs {
				fmt.Fprintf(buf, "Pod `%s` logs\n\n```\n%s\n```\n\n", podName, logs)
			}
			body = buf.String()
		} else {
			subject = "Job completed"
			body = formatJob(job, false)
		}

		notifier.Send(context.Background(), subject, body)
	}
}

func getManagedPods(job *batchv1.Job) ([]corev1.Pod, error) {
	pods, err := clientset.CoreV1().Pods(job.Namespace).List(context.TODO(), v1.ListOptions{
		LabelSelector: fmt.Sprintf("controller-uid=%s", job.UID),
	})
	return pods.Items, err
}

func getPodLogs(pod corev1.Pod) (string, error) {
	req := clientset.CoreV1().Pods(pod.Namespace).GetLogs(pod.Name, &corev1.PodLogOptions{})
	logs, err := req.Stream(context.TODO())
	if err != nil {
		return "", err
	}
	defer logs.Close()

	buf := new(bytes.Buffer)
	_, err = io.Copy(buf, logs)
	if err != nil {
		return "", nil
	}
	return buf.String(), nil
}

func collectJobOutputs(job *batchv1.Job) (map[string]string, error) {
	managedPods, err := getManagedPods(job)
	if err != nil {
		return nil, err
	}

	result := make(map[string]string, len(managedPods))

	for _, pod := range managedPods {
		logs, err := getPodLogs(pod)
		if err != nil {
			return nil, err
		}
		result[pod.Name] = logs
	}

	return result, nil
}

func formatJob(job *batchv1.Job, markdown bool) string {
	printMap := func(dest io.Writer, m map[string]string) {
		for key, value := range m {
			if markdown {
				fmt.Fprintf(dest, "· `%s: %s`\n", key, value)
			} else {
				fmt.Fprintf(dest, "  %s: %s\n", key, value)
			}
		}
	}

	msg := new(strings.Builder)

	if markdown {
		fmt.Fprintf(msg, "\nJob `%s` [%d/%d/%d]\n", job.Name, job.Status.Active, job.Status.Succeeded, job.Status.Failed)
	} else {
		fmt.Fprintf(msg, "Job %q [%d/%d/%d]\n", job.Name, job.Status.Active, job.Status.Succeeded, job.Status.Failed)
	}

	// Labels
	if len(job.Labels) > 0 {
		msg.WriteString("\n*Labels*\n\n")
		printMap(msg, job.Labels)
	}

	// Annotations
	if len(job.Annotations) > 0 {
		msg.WriteString("\n*Annotations*\n\n")
		printMap(msg, job.Annotations)
	}

	// Managed Pods
	pods, _ := getManagedPods(job)
	if len(pods) > 0 {
		msg.WriteString("\n*Managed pods*\n\n")
		for _, pod := range pods {
			if markdown {
				fmt.Fprintf(msg, "- Pod `%s`, state `%s`\n", pod.Name, pod.Status.Phase)
			} else {
				fmt.Fprintf(msg, "- Pod %q, state %s\n", pod.Name, pod.Status.Phase)
			}
		}
	}

	if markdown {
		msg.WriteString("\n\n")
	} else {
		msg.WriteString("---\n")
	}
	return msg.String()
}

func watchJobs(namespace string) {
	log.Info("Watching jobs in namespace ", namespace)

	informerFactory := kubeinformers.NewSharedInformerFactoryWithOptions(clientset, 10*time.Minute, kubeinformers.WithNamespace(namespace))
	jobsInformer := informerFactory.Batch().V1().Jobs().Informer()

	jobsInformer.AddEventHandler(
		cache.ResourceEventHandlerFuncs{
			UpdateFunc: handleUpdate,
		},
	)
	stop := make(chan struct{})
	go informerFactory.Start(stop)
	if !cache.WaitForCacheSync(stop, jobsInformer.HasSynced) {
		log.Fatal("Timed out waiting for initial cache sync")
	}
}

func main() {
	log.SetLevel(log.DebugLevel)
	log.SetFormatter(&log.TextFormatter{
		DisableTimestamp: true,
		DisableQuote:     true,
		ForceColors:      true,
	})

	namespace := corev1.NamespaceDefault
	watchJobs(namespace)

	select {}
}
