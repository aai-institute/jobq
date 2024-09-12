package notify

import (
	"os"
	"strings"

	log "github.com/sirupsen/logrus"

	"github.com/nikoksr/notify"
	http "github.com/nikoksr/notify/service/http"
	slack "github.com/nikoksr/notify/service/slack"
)

const (
	AnnotationKeyNotifyChannel   = "x-jobby.io/notify-channel"
	AnnotationKeySlackChannelIds = "x-jobby.io/slack-channel-ids"
	AnnotationKeyWebhookURLs     = "x-jobby.io/webhook-urls"
)

type NotifierKey string

const (
	NotifierSlack   NotifierKey = "slack"
	NotifierWebhook NotifierKey = "webhook"
)

const (
	EnvSlackApiToken = "WATCHER_SLACK_API_TOKEN"
)

func GetNotifierKey(annotations map[string]string) NotifierKey {
	notifier := annotations[AnnotationKeyNotifyChannel]
	return NotifierKey(notifier)
}

func GetNotifier(key NotifierKey, jobAnnotations map[string]string) notify.Notifier {
	switch key {
	case NotifierSlack:
		log.Debug("Using Slack notifier")
		service := slack.New(os.Getenv(EnvSlackApiToken))
		receivers := jobAnnotations[AnnotationKeySlackChannelIds]
		log.Debug("Slack notifier channel IDs: ", receivers)

		if receivers == "" {
			return nil
		}
		service.AddReceivers(strings.Split(receivers, ",")...)
		return service

	case NotifierWebhook:
		log.Debug("Using Webhook notifier")
		service := http.New()
		receivers := jobAnnotations[AnnotationKeyWebhookURLs]
		log.Debug("Webhook notifier URLs: ", receivers)

		if receivers == "" {
			return nil
		}
		service.AddReceiversURLs(strings.Split(receivers, ",")...)
		return service
	}
	return nil
}
