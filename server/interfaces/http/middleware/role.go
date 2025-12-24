package middleware

import (
	"fmt"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/infrastructure/zitadel"
	"github.com/gofiber/fiber/v2"
	"github.com/spf13/viper"
)

const RoleCtxKey = "role-ctx-key"

func RoleAuthorization() fiber.Handler {
	return func(c *fiber.Ctx) error {
		authCtx := zitadel.ZitadelInterceptor.Context(c.Context())
		orgID := c.Locals(OrganizationCtxKey).(string)

		orgsRole := ""

		claimScope := fmt.Sprintf("urn:zitadel:iam:org:project:%s:roles", viper.GetString("zitadel_project_id"))
		if claimValue, ok := authCtx.Claims[claimScope].(map[string]any); ok {
			for role, orgs := range claimValue {
				if orgsMap, ok := orgs.(map[string]any); ok {
					for key := range orgsMap {
						if key == orgID {
							if orgsRole == "" {
								orgsRole = role
							} else if role == string(models.Admin) {
								orgsRole = role
							}
						}
					}
				}
			}
		}

		c.Locals(RoleCtxKey, models.Role(orgsRole))
		return c.Next()
	}
}
