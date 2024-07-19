package cmd

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/factly/gopie/config"
	"github.com/factly/gopie/pkg"
	"github.com/spf13/cobra"
	"golang.org/x/sync/errgroup"
)

func init() {
	rootCmd.AddCommand(detachCmd)
}

var detachCmd = &cobra.Command{
	Use:   "detach",
	Short: "Detaches all the attached databases on gopie",
	Run: func(cmd *cobra.Command, args []string) {
		detach()
	},
}

func detach() {
	cfg, logger, err := setupConfig()
	if err != nil {
		log.Fatal("Error setting up config: ", err)
	}

	client := &http.Client{Timeout: 30 * time.Second}
	dbs, err := getDatabases(client, cfg.D.GopieUrl, cfg.Auth.Mastkey)
	if err != nil {
		logger.Error("Error getting databases", "error", err)
		return
	}

	if len(dbs) == 0 {
		logger.Info("no databases to detach")
		return
	}

	ctx := context.Background()
	g, ctx := errgroup.WithContext(ctx)
	g.SetLimit(10)
	for _, db := range dbs {
		db := db
		g.Go(func() error {
			logger.Info("detaching", "database", db)
			if err := detachDatabase(client, cfg.D.GopieUrl, cfg.Auth.Mastkey, db); err != nil {
				logger.Error("Error detaching database", "error", err, "database", db)
				return err
			}
			logger.Info("succesfully detached", "database", db)
			return nil
		})

	}

	if err := g.Wait(); err != nil {
		logger.Error("Error occurred during database detachment", "error", err)
	}
}

func setupConfig() (*config.Config, *pkg.Logger, error) {
	config := config.New()
	cfg, err := config.LoadConfig()
	if err != nil {
		return nil, nil, fmt.Errorf("error loading config: %w", err)
	}

	logger := pkg.NewLogger()
	if err := logger.SetConfig(&cfg.Logger); err != nil {
		return nil, nil, fmt.Errorf("error setting logger config: %w", err)
	}

	return cfg, logger, nil
}

func getDatabases(client *http.Client, url, mk string) ([]string, error) {
	req, err := http.NewRequest("GET", fmt.Sprintf("%s/metrics/databases", url), nil)
	if err != nil {
		return nil, fmt.Errorf("error creating request: %w", err)
	}
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", mk))

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("error sending request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var databases []string
	if err := json.NewDecoder(resp.Body).Decode(&databases); err != nil {
		return nil, fmt.Errorf("error decoding response: %w", err)
	}

	return databases, nil
}

func detachDatabase(client *http.Client, url, mk, database string) error {
	body := map[string]string{"table_name": database}
	jsonBody, err := json.Marshal(body)
	if err != nil {
		return fmt.Errorf("error marshalling body: %w", err)
	}

	req, err := http.NewRequest("POST", fmt.Sprintf("%s/source/detach", url), bytes.NewReader(jsonBody))
	if err != nil {
		return fmt.Errorf("error creating request: %w", err)
	}
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", mk))
	req.Header.Set("Content-Type", "application/json")

	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("error sending request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	return nil
}
