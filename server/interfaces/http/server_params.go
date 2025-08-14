package http

import (
	"github.com/factly/gopie/application/services"
	"github.com/factly/gopie/domain/pkg/logger"
)

// ServerParams holds all the repositories and services needed by the servers
type ServerParams struct {
	// Logger
	Logger *logger.Logger

	// Services
	OlapService      *services.OlapService
	AIService        *services.AiDriver
	ProjectService   *services.ProjectService
	DatasetService   *services.DatasetService
	ChatService      *services.ChatService
	AIAgentService   *services.AIService
	DbSourceService  *services.DatabaseSourceService
	DownloadsService *services.DownloadServerService
}
