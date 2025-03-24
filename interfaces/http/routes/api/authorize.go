package api

import (
	"fmt"
	"io"
	"net/http"
	"net/url"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
)

func (h *httpHandler) authorize(ctx *fiber.Ctx) error {
	targetURL := h.config.Zitadel.Protocol + "://" + h.config.Zitadel.Domain

	if h.config.Zitadel.Protocol == "http" {
		targetURL += ":" + h.config.Zitadel.InsecurePort
	}

	targetURL += "/oauth/v2/authorize"

	// Get query parameters from the Fiber context
	params := url.Values{}
	ctx.Request().URI().QueryArgs().VisitAll(func(key, value []byte) {
		params.Add(string(key), string(value))
	})

	proxyURL := fmt.Sprintf("%s?%s", targetURL, params.Encode())

	// Perform the proxy request
	req, err := http.NewRequest("GET", proxyURL, nil)
	if err != nil {
		h.logger.Info("Error creating request", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).SendString("Failed to create request")
	}

	req.Header.Set("X-Zitadel-Login-Client", h.config.Zitadel.ServiceUserID)
	client := &http.Client{
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			return http.ErrUseLastResponse
		},
	}

	resp, err := client.Do(req)
	if err != nil {
		h.logger.Info("Error performing request", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).SendString("Failed to perform request")
	}
	defer resp.Body.Close()

	// Handle the response
	location := resp.Header.Get("Location")
	if location == "" {
		body, err := io.ReadAll(resp.Body)
		if err != nil {
			h.logger.Error("Error reading response body", zap.Error(err))
			return ctx.Status(fiber.StatusBadRequest).SendString("Failed to decode callback URL: " + err.Error())
		}
		h.logger.Error("Failed to get location header", zap.String("body", string(body)))
		return ctx.Status(fiber.StatusInternalServerError).SendString("Failed to get location header: err: " + string(body))
	}

	parsedURL, err := url.Parse(location)
	if err != nil {
		h.logger.Error("Failed to parse location URL", zap.Error(err))
		return ctx.Status(fiber.StatusInternalServerError).SendString("Failed to parse location URL: " + err.Error())
	}

	authRequestID := parsedURL.Query().Get("authRequest")
	if authRequestID == "" {
		h.logger.Error("authRequest parameter is required")
		return ctx.Status(fiber.StatusInternalServerError).SendString("authRequest parameter is required")
	}

	redirectURL := fmt.Sprintf(h.config.Zitadel.LoginURL+"?authRequest=%s", authRequestID)
	return ctx.Redirect(redirectURL, fiber.StatusSeeOther)
}
