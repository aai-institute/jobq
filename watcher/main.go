package main

import (
	"context"
	"time"
	"watcher/pkg/compose"
	"watcher/pkg/notify"
	util "watcher/pkg/util"

	log "github.com/sirupsen/logrus"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/cache"
	kueue "sigs.k8s.io/kueue/apis/kueue/v1beta1"
	kueueversioned "sigs.k8s.io/kueue/client-go/clientset/versioned"
	kueueev "sigs.k8s.io/kueue/client-go/informers/externalversions"
)

var (
	config, _        = util.GetKubeConfig()
	clientset, _     = kubernetes.NewForConfig(config)
	dynamicClient, _ = dynamic.NewForConfig(config)
	kueueClient, _   = kueueversioned.NewForConfig(config)
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
	useMarkdown := notifierKey == notify.NotifierSlack
	event := util.GetEventType(oldWl, wl)
	if event != util.NoEvent {
		composer := compose.NewComposer(useMarkdown, clientset, dynamicClient, kueueClient)
		message := composer.Compose(event, wl, oldWl, newJob, job)
		err = notifier.Send(context.Background(), message.Subject, message.Body)
		if err != nil {
			log.Warn("Could not send notification: ", err)
		}
	}
}

// Watch Kueue workloads for lifecycle updates
func watchWorkloads(namespace string) {
	log.Info("Watching Kueue Workloads in namespace ", namespace)

	factory := kueueev.NewSharedInformerFactoryWithOptions(kueueClient, 10*time.Minute, kueueev.WithNamespace(namespace))

	workloadInformer := factory.Kueue().V1beta1().Workloads().Informer()
	_, err := workloadInformer.AddEventHandler(
		cache.ResourceEventHandlerFuncs{
			UpdateFunc: handleUpdate,
		},
	)
	if err != nil {
		log.Fatal("Could not add event handler: ", err)
	}
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
