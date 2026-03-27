package middleware

import (
	"context"
	"errors"
	"net/url"
	"strings"

	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/logger"
	gen "github.com/factly/gopie/infrastructure/postgres/gen"
	"github.com/gofiber/fiber/v2"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"go.uber.org/zap"
)

const (
	UserCtxKey         = "x-user-id"
	OrganizationCtxKey = "x-organization-id"
	RoleCtxKey         = "x-role"

	// Better Auth session cookie names
	// In production with secure cookies, browsers send the __Secure- prefixed name
	// For requests proxied through Next.js API, the non-prefixed name is used
	BetterAuthSessionCookie       = "better-auth.session_token"
	BetterAuthSessionCookieSecure = "__Secure-better-auth.session_token"
)

// BetterAuthMiddleware validates session token from cookie and sets user context.
// useSecureCookie selects the __Secure- prefixed cookie name (true for production/HTTPS)
// or the plain cookie name (false for development/HTTP).
func BetterAuthMiddleware(pool *pgxpool.Pool, logger *logger.Logger, useSecureCookie bool) fiber.Handler {
	return betterAuthHandler(pool, logger, useSecureCookie)
}

// betterAuthHandler is the internal implementation that accepts the DBTX interface
// for testability. BetterAuthMiddleware delegates to this function.
func betterAuthHandler(db gen.DBTX, logger *logger.Logger, useSecureCookie bool) fiber.Handler {
	queries := gen.New(db)

	cookieName := BetterAuthSessionCookie
	if useSecureCookie {
		cookieName = BetterAuthSessionCookieSecure
	}

	return func(c *fiber.Ctx) error {
		token := c.Cookies(cookieName)
		if token == "" {
			logger.Error("Better Auth session cookie missing")
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error":   "unauthorized",
				"message": "session cookie is required",
			})
		}

		// URL decode the token (browser may send it URL-encoded)
		decodedToken, err := url.QueryUnescape(token)
		if err != nil {
			logger.Error("Failed to decode session token", zap.Error(err))
			decodedToken = token // fallback to original if decode fails
		}

		// Better Auth token format: "sessionId.signature"
		// Database stores only the sessionId part
		sessionId := decodedToken
		if dotIndex := strings.Index(decodedToken, "."); dotIndex != -1 {
			sessionId = decodedToken[:dotIndex]
		}

		// Validate session by token
		userID, err := queries.GetSessionByToken(context.Background(), sessionId)
		if err != nil {
			if errors.Is(err, pgx.ErrNoRows) {
				logger.Error("Invalid or expired session", zap.Error(err))
				return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
					"error":   "unauthorized",
					"message": "invalid or expired session",
				})
			}
			// Database error
			logger.Error("Database error while validating session", zap.Error(err))
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   "internal_error",
				"message": "failed to validate session",
			})
		}

		// Set user ID in context
		c.Locals(UserCtxKey, userID)

		// Get organization ID from header
		orgID := c.Get(OrganizationCtxKey)
		if orgID == "" {
			logger.Error("Organization ID header missing",
				zap.String("userId", userID))
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error":   "bad_request",
				"message": "x-organization-id header is required",
			})
		}

		c.Locals(OrganizationCtxKey, orgID)

		// Get user role
		role, err := queries.GetUserRole(context.Background(), userID)
		if err != nil {
			if errors.Is(err, pgx.ErrNoRows) {
				logger.Error("User not found", zap.String("userId", userID))
				return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
					"error":   "unauthorized",
					"message": "user not found",
				})
			}
			logger.Error("Database error while fetching user role", zap.Error(err))
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   "internal_error",
				"message": "failed to fetch user role",
			})
		}

		c.Locals(RoleCtxKey, models.Role(role))

		return c.Next()
	}
}

// AuthorizeHeaders is used when auth is disabled (GOPIE_ENABLE_AUTH=false).
// It reads user and org IDs from request headers directly.
func AuthorizeHeaders(logger *logger.Logger) fiber.Handler {
	return func(c *fiber.Ctx) error {
		// Extract user ID from the request context
		userID := c.Get(UserCtxKey)
		if userID == "" {
			logger.Error("User ID not found in request context")
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "user ID not found",
			})
		}
		c.Locals(UserCtxKey, userID)

		orgID := c.Get(OrganizationCtxKey)
		if orgID == "" {
			logger.Error("Organization ID not found in request context", zap.String("userID", userID))
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "organization ID not found",
			})
		}
		c.Locals(OrganizationCtxKey, orgID)

		c.Locals(RoleCtxKey, models.Admin)
		return c.Next()
	}
}

func APIAuth(logger *logger.Logger) fiber.Handler {
	return func(c *fiber.Ctx) error {
		// Extract user ID from the request context
		userID := c.Get(UserCtxKey)
		if userID == "" {
			logger.Error("User ID not found in request context")
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "user ID not found",
			})
		}
		c.Locals(UserCtxKey, userID)

		orgID := c.Get(OrganizationCtxKey)
		if orgID == "" {
			logger.Error("Organization ID not found in request context", zap.String("userID", userID))
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "organization ID not found",
			})
		}
		c.Locals(OrganizationCtxKey, orgID)

		c.Locals(RoleCtxKey, models.Admin)
		return c.Next()
	}
}
