package zitadel

import (
	"context"

	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	"github.com/zitadel/zitadel-go/v3/pkg/authorization"
	"github.com/zitadel/zitadel-go/v3/pkg/authorization/oauth"
	"github.com/zitadel/zitadel-go/v3/pkg/http/middleware"
	"github.com/zitadel/zitadel-go/v3/pkg/zitadel"
	"go.uber.org/zap"
)

var ZitadelInterceptor *middleware.Interceptor[*oauth.IntrospectionContext]

func SetupZitadelInterceptor(cfg *config.GoPieConfig, logger *logger.Logger) {
	ctx := context.Background()

	zt := zitadel.New(cfg.Zitadel.Domain)

	if cfg.Zitadel.Protocol == "http" {
		zt = zitadel.New(cfg.Zitadel.Domain, zitadel.WithInsecure(cfg.Zitadel.InsecurePort))
	}

	authZ, err := authorization.New(ctx, zt, oauth.DefaultAuthorization("./zitadel_key.json"))
	if err != nil {
		logger.Fatal("failed to create zitadel authorization", zap.Error(err))
		return
	}

	logger.Info("zitadel interceptor initialized")

	ZitadelInterceptor = middleware.New(authZ)
}
