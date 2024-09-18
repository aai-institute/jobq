package compose

import (
	"fmt"
	"strings"
	"watcher/pkg/util"

	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	kueue "sigs.k8s.io/kueue/apis/kueue/v1beta1"
	kueueversioned "sigs.k8s.io/kueue/client-go/clientset/versioned"
)

type Message struct {
	Subject string
	Body    string
}

type Composer interface {
	Compose(event util.LifecycleEvent, wl, oldWl *kueue.Workload, newJob, job *unstructured.Unstructured) Message
}

type PlainTextComposer struct {
	client        kubernetes.Interface
	dynamicClient dynamic.Interface
	kueueClient   kueueversioned.Interface
}
type MarkdownComposer struct {
	client        kubernetes.Interface
	dynamicClient dynamic.Interface
	kueueClient   kueueversioned.Interface
}

func NewComposer(useMarkdown bool, client kubernetes.Interface, dynamicClient dynamic.Interface, kueueClient kueueversioned.Interface) Composer {
	if useMarkdown {
		return &MarkdownComposer{client: client, dynamicClient: dynamicClient, kueueClient: kueueClient}
	}
	return &PlainTextComposer{client: client, dynamicClient: dynamicClient, kueueClient: kueueClient}
}

func (p *PlainTextComposer) Compose(event util.LifecycleEvent, wl, oldWl *kueue.Workload, newJob, job *unstructured.Unstructured) Message {
	message := Message{}

	switch event {
	case util.EvictionEvent:
		{
			preemptor, _ := util.GetPreemptingWorkload(p.kueueClient, wl)
			message.Subject = fmt.Sprintf("Workload %q was preempted", wl.Name)
			message.Body = fmt.Sprintf("Preempting workload: `%s`", preemptor.Name)
			if wl.Namespace != preemptor.Namespace {
				message.Body += fmt.Sprintf(" (in namespace %q)", preemptor.Namespace)
			}
		}
	case util.AdmissionEvent:
		{
			builder := new(strings.Builder)
			fmt.Fprintln(builder)

			fmt.Fprintln(builder, "Namespace: ", wl.Namespace)
			fmt.Fprintln(builder, "Local queue: ", wl.Spec.QueueName)
			fmt.Fprintln(builder, "Cluster queue: ", wl.Status.Admission.ClusterQueue)
			fmt.Fprintf(builder, "Managed resource: %s/%s\n", newJob.GetKind(), newJob.GetName())

			message.Subject = fmt.Sprintf("Workload %q was admitted to cluster queue", wl.Name)
			message.Body = builder.String()
		}

	case util.CompletionEvent:
		{
			message.Subject = fmt.Sprintf("Workload %q is completed", wl.Name)
			message.Body = ""
		}

	case util.FailureEvent:
		{
			message.Subject = fmt.Sprintf("Workload %q has failed", wl.Name)
			message.Body = ""
		}
	}
	return message
}

func (m *MarkdownComposer) Compose(event util.LifecycleEvent, wl, oldWl *kueue.Workload, newJob, job *unstructured.Unstructured) Message {
	message := Message{}
	switch event {
	case util.EvictionEvent:
		{
			preemptor, _ := util.GetPreemptingWorkload(m.kueueClient, wl)
			message.Subject = fmt.Sprintf(":octagonal_sign: *Workload `%s` was preempted*", wl.Name)
			message.Body = fmt.Sprintf("Preempting workload: `%s`", preemptor.Name)
			if wl.Namespace != preemptor.Namespace {
				message.Body += fmt.Sprintf(" (in namespace `%s`)", preemptor.Namespace)
			}
		}

	case util.AdmissionEvent:
		{
			builder := new(strings.Builder)
			fmt.Fprintln(builder)

			fmt.Fprintf(builder, "Namespace: `%s`\n", wl.Namespace)
			fmt.Fprintf(builder, "User queue: `%s`\n", wl.Spec.QueueName)
			fmt.Fprintf(builder, "Cluster queue: `%s`\n", wl.Status.Admission.ClusterQueue)
			fmt.Fprintf(builder, "Managed resource: `%s/%s`\n", newJob.GetKind(), newJob.GetName())

			message.Subject = fmt.Sprintf(":clapper: *Workload `%s` was admitted*", wl.Name)
			message.Body = builder.String()
		}

	case util.CompletionEvent:
		{
			builder := new(strings.Builder)
			fmt.Fprintln(builder)

			totalTime, _ := util.GetTotalExecutionTime(wl)
			activeTime, _ := util.GetActiveExecutionTime(wl)
			fmt.Fprintln(builder, "Total execution time (since submission): ", totalTime)
			fmt.Fprintln(builder, "Active execution time (since last queue admission): ", activeTime)
			fmt.Fprintln(builder)

			outputs, err := util.CollectOutputs(m.client, m.dynamicClient, wl)
			if err == nil {
				for podName, logs := range outputs {
					fmt.Fprintf(builder, "*Pod `%s` logs*\n\n```\n%s\n```\n\n", podName, logs)
				}
			}
			message.Subject = fmt.Sprintf(":white_check_mark: *Workload `%s` is completed*", wl.Name)
			message.Body = builder.String()
		}

	case util.FailureEvent:
		{
			buf := new(strings.Builder)
			outputs, err := util.CollectOutputs(m.client, m.dynamicClient, wl)

			if err == nil {
				buf.WriteString("\n")
				for podName, logs := range outputs {
					fmt.Fprintf(buf, "Pod `%s` logs\n\n```\n%s\n```\n\n", podName, logs)
				}
			}
			message.Subject = fmt.Sprintf(":rotating_light: *Workload `%s` has failed*", wl.Name)
			message.Body = buf.String()
		}
	}

	return message
}
