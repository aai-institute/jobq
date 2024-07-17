package util

import (
	"context"
	"fmt"
	"regexp"
	"time"

	batchv1 "k8s.io/api/batch/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/apimachinery/pkg/watch"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/cache"
	kueue "sigs.k8s.io/kueue/apis/kueue/v1beta1"
	kueueversioned "sigs.k8s.io/kueue/client-go/clientset/versioned"
)

func NewKueueWorkloadInformer(client kueueversioned.Interface, resyncPeriod time.Duration) cache.SharedIndexInformer {
	return cache.NewSharedIndexInformer(
		&cache.ListWatch{
			ListFunc: func(options metav1.ListOptions) (runtime.Object, error) {
				return client.KueueV1beta1().Workloads("").List(context.TODO(), options)
			},
			WatchFunc: func(options metav1.ListOptions) (watch.Interface, error) {
				return client.KueueV1beta1().Workloads("").Watch(context.TODO(), options)
			},
		},
		&kueue.Workload{},
		resyncPeriod,
		cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc},
	)
}

// Find a Kueue Workload by its UID, optionally filtered by namespace
func WorkloadByUid(kueueClient kueueversioned.Interface, uid types.UID, namespace string) (*kueue.Workload, error) {
	list, err := kueueClient.KueueV1beta1().Workloads(namespace).List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		return nil, err
	}
	for _, item := range list.Items {
		if item.GetUID() == uid {
			return &item, nil
		}
	}
	return nil, fmt.Errorf("workload with UID %q not found", uid)
}

// Get a workload condition status by its type and optionally reason (empty string disables the filter)
func GetWorkloadCondition(wl *kueue.Workload, ctype, reason string) (*metav1.Condition, bool) {
	for _, cond := range wl.Status.Conditions {
		// Either no reason filter was given or it matches the condition
		if cond.Type == ctype && (reason == "" || cond.Reason == reason) {
			return &cond, true
		}
	}
	return nil, false
}

// Get the total (i.e., after being created) execution time of a finished Kueue workload
func GetTotalExecutionTime(wl *kueue.Workload) (time.Duration, error) {
	completion, found := GetWorkloadCondition(wl, kueue.WorkloadFinished, kueue.WorkloadFinishedReasonSucceeded)
	if !found {
		return 0, fmt.Errorf("workload is not completed successfully: %s", wl.Name)
	}
	return completion.LastTransitionTime.Sub(wl.ObjectMeta.CreationTimestamp.Time), nil
}

// Get the active (i.e., after being admitted) execution time of a finished Kueue workload
func GetActiveExecutionTime(wl *kueue.Workload) (time.Duration, error) {
	completion, found := GetWorkloadCondition(wl, kueue.WorkloadFinished, kueue.WorkloadFinishedReasonSucceeded)
	if !found {
		return 0, fmt.Errorf("workload is not completed successfully: %s", wl.Name)
	}

	admission, found := GetWorkloadCondition(wl, kueue.WorkloadAdmitted, kueue.WorkloadAdmitted)
	if !found {
		return 0, fmt.Errorf("workload was never admitted (?!): %s", wl.Name)
	}

	return completion.LastTransitionTime.Sub(admission.LastTransitionTime.Time), nil
}

func GetPreemptingWorkload(kueueClient kueueversioned.Interface, wl *kueue.Workload) (*kueue.Workload, error) {
	preemption, found := GetWorkloadCondition(wl, kueue.WorkloadPreempted, "")
	if !found {
		return nil, fmt.Errorf("workload was not preempted: %s", wl.Name)
	}
	re, _ := regexp.Compile("UID: ([^)]+)")
	uid := re.FindStringSubmatch(preemption.Message)[1]
	if uid == "" {
		return nil, fmt.Errorf("could not extract preemptor UID from condition message: %s", preemption.Message)
	}
	preemptor, err := WorkloadByUid(kueueClient, types.UID(uid), "")
	return preemptor, err
}

// Find the associated Job for a Kueue Workload resource
// FIXME: Ugly signature
func GetManagedResource(clientset kubernetes.Interface, dynamicClient dynamic.Interface, workload *kueue.Workload) (*unstructured.Unstructured, error) {
	if len(workload.OwnerReferences) != 1 {
		return nil, fmt.Errorf("workload does not have exactly one owner reference: %s", workload.Name)
	}

	ownerRef, _ := Last(workload.OwnerReferences)
	gv, _ := schema.ParseGroupVersion(ownerRef.APIVersion)
	resource, err := KindToResource(clientset, gv.WithKind(ownerRef.Kind))
	if err != nil {
		return nil, err
	}
	gvk := gv.WithResource(resource)

	obj, err := dynamicClient.Resource(gvk).Namespace(workload.Namespace).Get(context.TODO(), ownerRef.Name, metav1.GetOptions{})
	if err != nil {
		return nil, err
	}
	return obj, nil
}

func CollectOutputs(clientset kubernetes.Interface, dynamicClient dynamic.Interface, wl *kueue.Workload) (map[string]string, error) {
	res, err := GetManagedResource(clientset, dynamicClient, wl)
	if err != nil {
		return nil, err
	}

	if res.GetKind() != "Job" {
		return nil, fmt.Errorf("managed resource is not a job: %s/%s", res.GetKind(), res.GetName())
	}

	job := batchv1.Job{}
	err = runtime.DefaultUnstructuredConverter.FromUnstructured(res.Object, &job)
	if err != nil {
		return nil, err
	}

	return CollectJobOutputs(clientset, &job)
}

// Check if a Kueue workload is successfully completed
func IsCompleted(wl *kueue.Workload) bool {
	_, found := GetWorkloadCondition(wl, kueue.WorkloadFinished, kueue.WorkloadFinishedReasonSucceeded)
	return found
}

// Check if a Kueue workload is failed
func IsFailed(wl *kueue.Workload) bool {
	_, found := GetWorkloadCondition(wl, kueue.WorkloadFinished, kueue.WorkloadFinishedReasonFailed)
	return found
}

// Check if a Kueue workload was preempted
func WasPreempted(oldWl, wl *kueue.Workload) bool {
	if oldWl.Status.Admission == nil {
		return false
	}

	if oldWl.Status.Admission != nil && wl.Status.Admission == nil {
		return true
	}

	return false
}

// Check if a Kueue workload was admitted to a queue
func WasAdmitted(oldWl, wl *kueue.Workload) bool {
	if wl.Status.Admission == nil {
		return false
	}

	if oldWl.Status.Admission == nil && wl.Status.Admission != nil {
		return true
	}

	return false
}
