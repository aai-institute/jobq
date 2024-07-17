package main

import (
	"context"
	"fmt"
	"os"
	"strings"
	"time"
	"watcher/pkg/notify"
	util "watcher/pkg/util"

	log "github.com/sirupsen/logrus"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/cli-runtime/pkg/genericclioptions"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/tools/clientcmd"
	kueue "sigs.k8s.io/kueue/apis/kueue/v1beta1"
	kueueev "sigs.k8s.io/kueue/client-go/informers/externalversions"
	kueueutil "sigs.k8s.io/kueue/cmd/experimental/kjobctl/pkg/cmd/util"
)

var (
	config, _        = clientcmd.BuildConfigFromFlags("", os.Getenv("KUBECONFIG"))
	clientset, _     = kubernetes.NewForConfig(config)
	dynamicClient, _ = dynamic.NewForConfig(config)
	kueueClient, _   = kueueutil.NewClientGetter(genericclioptions.NewConfigFlags(false)).KueueClientset()
)

func handleUpdate(obj, newObj interface{}) {
	oldWl := obj.(*kueue.Workload)
	wl := newObj.(*kueue.Workload)

	job, err := util.GetManagedResource(clientset, dynamicClient, oldWl)
	if job == nil || err != nil {
		log.Warn("Could not retrieve managed resource for workload ", oldWl.Name, err)
		return
	}

	newJob, err := util.GetManagedResource(clientset, dynamicClient, wl)
	if newJob == nil || err != nil {
		log.Warn("Could not retrieve managed resource for workload ", wl.Name, err)
		return
	}

	notifierKey := notify.GetNotifierKey(job.GetAnnotations())
	notifier := notify.GetNotifier(notifierKey, newJob.GetAnnotations())
	if notifier == nil {
		log.Warnf("Could not determine notifier, %+v\n", job.GetAnnotations())
		return
	}
	useMarkdown := notifierKey == "slack"

	var body, subject string

	if util.WasPreempted(oldWl, wl) {
		preemptor, _ := util.GetPreemptingWorkload(kueueClient, wl)
		if useMarkdown {
			subject = fmt.Sprintf(":octagonal_sign: *Workload `%s` was preempted*", wl.Name)
			body = fmt.Sprintf("Preempting workload: `%s`", preemptor.Name)
			if wl.Namespace != preemptor.Namespace {
				body += fmt.Sprintf(" (in namespace `%s`)", preemptor.Namespace)
			}
		} else {
			subject = fmt.Sprintf("Workload %q was preempted", wl.Name)
			body = fmt.Sprintf("Preempting workload: `%s`", preemptor.Name)
			if wl.Namespace != preemptor.Namespace {
				body += fmt.Sprintf(" (in namespace %q)", preemptor.Namespace)
			}
		}
		notifier.Send(context.Background(), subject, body)
	}

	if util.WasAdmitted(oldWl, wl) {
		if useMarkdown {
			builder := new(strings.Builder)
			fmt.Fprintln(builder)

			fmt.Fprintf(builder, "Namespace: `%s`\n", wl.Namespace)
			fmt.Fprintf(builder, "User queue: `%s`\n", wl.Spec.QueueName)
			fmt.Fprintf(builder, "Cluster queue: `%s`\n", wl.Status.Admission.ClusterQueue)
			fmt.Fprintf(builder, "Managed resource: `%s/%s`\n", newJob.GetKind(), newJob.GetName())

			subject = fmt.Sprintf(":clapper: *Workload `%s` was admitted*", wl.Name)
			body = builder.String()
		} else {
			builder := new(strings.Builder)
			fmt.Fprintln(builder)

			fmt.Fprintln(builder, "Namespace: ", wl.Namespace)
			fmt.Fprintln(builder, "Local queue: ", wl.Spec.QueueName)
			fmt.Fprintln(builder, "Cluster queue: ", wl.Status.Admission.ClusterQueue)
			fmt.Fprintf(builder, "Managed resource: %s/%s\n", newJob.GetKind(), newJob.GetName())

			subject = fmt.Sprintf("Workload %q was admitted to cluster queue", wl.Name)
			body = builder.String()
		}
		notifier.Send(context.Background(), subject, body)
	}

	if !util.IsCompleted(oldWl) && util.IsCompleted(wl) {
		if useMarkdown {
			builder := new(strings.Builder)
			fmt.Fprintln(builder)

			totalTime, _ := util.GetTotalExecutionTime(wl)
			activeTime, _ := util.GetActiveExecutionTime(wl)
			fmt.Fprintln(builder, "Total execution time (since submission): ", totalTime)
			fmt.Fprintln(builder, "Active execution time (since last queue admission): ", activeTime)
			fmt.Fprintln(builder)

			outputs, err := util.CollectOutputs(clientset, dynamicClient, wl)
			if err == nil {
				for podName, logs := range outputs {
					fmt.Fprintf(builder, "*Pod `%s` logs*\n\n```\n%s\n```\n\n", podName, logs)
				}
			} else {
				log.Warn("Could not get workload outputs: ", err)
			}

			subject = fmt.Sprintf(":white_check_mark: *Workload `%s` is completed*", wl.Name)
			body = builder.String()
		} else {
			subject = fmt.Sprintf("Workload %q is completed", wl.Name)
			body = ""
		}
		notifier.Send(context.Background(), subject, body)
	}

	if !util.IsFailed(oldWl) && util.IsFailed(wl) {
		if useMarkdown {
			buf := new(strings.Builder)
			outputs, err := util.CollectOutputs(clientset, dynamicClient, wl)

			if err == nil {
				buf.WriteString("\n")
				for podName, logs := range outputs {
					fmt.Fprintf(buf, "Pod `%s` logs\n\n```\n%s\n```\n\n", podName, logs)
				}
			} else {
				log.Warn("Could not get workload outputs: ", err)
			}

			subject = fmt.Sprintf(":rotating_light: *Workload `%s` has failed*", wl.Name)
			body = buf.String()
		} else {
			subject = fmt.Sprintf("Workload %q has failed", wl.Name)
			body = ""
		}
		notifier.Send(context.Background(), subject, body)
	}
}

// Watch Kueue workloads for lifecycle updates
func watchWorkloads(namespace string) {
	log.Info("Watching Kueue Workloads in namespace ", namespace)

	factory := kueueev.NewSharedInformerFactoryWithOptions(kueueClient, 10*time.Minute, kueueev.WithNamespace(namespace))

	workloadInformer := factory.Kueue().V1beta1().Workloads().Informer()
	workloadInformer.AddEventHandler(
		cache.ResourceEventHandlerFuncs{
			UpdateFunc: handleUpdate,
		},
	)
	stop := make(chan struct{})
	go workloadInformer.Run(stop)
	if !cache.WaitForCacheSync(stop, workloadInformer.HasSynced) {
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
	watchWorkloads(namespace)

	select {}
}
