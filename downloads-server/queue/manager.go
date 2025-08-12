package queue

import (
	"encoding/json"

	"github.com/factly/gopie/downlods-server/pkg/logger"
	"go.uber.org/zap"
)

type ProgressEvent struct {
	DownloadID string `json:"download_id"`
	Type       string `json:"type"`
	Message    string `json:"message"`
}

type SubscriptionManager struct {
	logger       *logger.Logger
	clients      map[string]map[chan string]bool
	broadcastCh  chan ProgressEvent
	registerCh   chan *clientSubscription
	unregisterCh chan *clientSubscription
}

type clientSubscription struct {
	downloadID string
	channel    chan string
}

func NewSubscriptionManager(log *logger.Logger) *SubscriptionManager {
	manager := &SubscriptionManager{
		logger:       log,
		clients:      make(map[string]map[chan string]bool),
		broadcastCh:  make(chan ProgressEvent),
		registerCh:   make(chan *clientSubscription),
		unregisterCh: make(chan *clientSubscription),
	}
	go manager.run()
	return manager
}

func (m *SubscriptionManager) run() {
	for {
		select {
		case sub := <-m.registerCh:
			if _, ok := m.clients[sub.downloadID]; !ok {
				m.clients[sub.downloadID] = make(map[chan string]bool)
			}
			m.clients[sub.downloadID][sub.channel] = true
			m.logger.Info("Client registered for SSE", zap.String("download_id", sub.downloadID))

		case sub := <-m.unregisterCh:

			if clientSet, ok := m.clients[sub.downloadID]; ok {
				if _, ok := clientSet[sub.channel]; ok {
					delete(clientSet, sub.channel)
					close(sub.channel)
					if len(clientSet) == 0 {
						delete(m.clients, sub.downloadID)
					}
				}
			}
			m.logger.Info("Client unregistered for SSE", zap.String("download_id", sub.downloadID))

		case event := <-m.broadcastCh:
			if clientSet, ok := m.clients[event.DownloadID]; ok {
				eventJSON, _ := json.Marshal(event)
				for clientCh := range clientSet {
					select {
					case clientCh <- string(eventJSON):
					default:
					}
				}
			}
		}
	}
}

// Subscribe adds a new client channel to listen for events for a specific download.
func (m *SubscriptionManager) Subscribe(downloadID string) chan string {
	ch := make(chan string, 10) // Buffered channel
	m.registerCh <- &clientSubscription{downloadID: downloadID, channel: ch}
	return ch
}

// Unsubscribe removes a client channel.
func (m *SubscriptionManager) Unsubscribe(downloadID string, ch chan string) {
	m.unregisterCh <- &clientSubscription{downloadID: downloadID, channel: ch}
}

// Broadcast sends a progress event to all clients subscribed to that download ID.
func (m *SubscriptionManager) Broadcast(event ProgressEvent) {
	m.broadcastCh <- event
}
