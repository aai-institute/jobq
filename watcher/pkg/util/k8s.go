package util

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"strings"

	batchv1 "k8s.io/api/batch/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
)

func CollectJobOutputs(clientset kubernetes.Interface, job *batchv1.Job) (map[string]string, error) {
	managedPods, err := GetManagedPods(clientset, job)
	if err != nil {
		return nil, err
	}

	result := make(map[string]string, len(managedPods))

	for _, pod := range managedPods {
		logs, err := GetPodLogs(clientset, pod)
		if err != nil {
			return nil, err
		}
		result[pod.Name] = logs
	}

	return result, nil
}

func GetManagedPods(clientset kubernetes.Interface, job *batchv1.Job) ([]corev1.Pod, error) {
	pods, err := clientset.CoreV1().Pods(job.Namespace).List(context.TODO(), metav1.ListOptions{
		LabelSelector: fmt.Sprintf("controller-uid=%s", job.UID),
	})
	return pods.Items, err
}

func GetPodLogs(clientset kubernetes.Interface, pod corev1.Pod) (string, error) {
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
	return strings.TrimSpace(buf.String()), nil
}
