package util

import (
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/restmapper"
)

func KindToResource(clientset kubernetes.Interface, gvk schema.GroupVersionKind) (string, error) {
	// Create a discovery client
	discoveryClient := clientset.Discovery()

	// Create a RESTMapper
	groupResources, err := restmapper.GetAPIGroupResources(discoveryClient)
	if err != nil {
		return "", err
	}
	mapper := restmapper.NewDiscoveryRESTMapper(groupResources)

	// Get the RESTMapping
	mapping, err := mapper.RESTMapping(gvk.GroupKind(), gvk.Version)
	if err != nil {
		return "", err
	}

	// Return the resource name
	return mapping.Resource.Resource, nil
}
