package notify

import (
	"os"
	"strings"

	log "github.com/sirupsen/logrus"

	"github.com/nikoksr/notify"
	http "github.com/nikoksr/notify/service/http"
	slack "github.com/nikoksr/notify/service/slack"
)

func GetNotifierKey(annotations map[string]string) string {
	notifier := annotations["x-jobby.io/notify-channel"]
	return notifier
}

func GetNotifier(key string, jobAnnotations map[string]string) notify.Notifier {
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
		service := http.New()
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
