package main

import (
	"context"
	"fmt"
	"log"

	"github.com/factly/gopie/config"
	"github.com/factly/gopie/duckdb"
	"github.com/factly/gopie/pkg"
)

func main() {
	driver := duckdb.Driver{}
	mappedCfg := make(map[string]any)
	mappedCfg["dsn"] = "./data/main.db"
	mappedCfg["external_table_storage"] = true
	mappedCfg["allow_host_access"] = true

	config := config.New()
	configService, err := config.LoadConfig()
	if err != nil {
		return
	}

	logger := pkg.NewLogger()
	err = logger.SetConfig(&configService.Logger)
	if err != nil {
		logger.Fatal("error setting logger config", "err", err.Error())
	}

	c, err := driver.Open(mappedCfg, *logger)
	if err != nil {
		logger.Error(err.Error())
	}

	res, err := c.Execute(context.Background(), &duckdb.Statement{Query: "SELECT * from electoral_bonds"})

	if err != nil {
		logger.Error(err.Error())
	}
	rows := res.Rows
	defer rows.Close()

	columns, err := rows.Columns()
	if err != nil {
		logger.Error(err.Error())
		return
	}

	values := make([]any, len(columns))
	valuePtrs := make([]any, len(columns))

	count := 0

	for rows.Next() {
		count++
		for i := range columns {
			valuePtrs[i] = &values[i]
		}

		err := rows.Scan(valuePtrs...)
		if err != nil {
			log.Fatal(err)
		}

		for i, col := range columns {
			val := values[i]
			fmt.Printf("%s: %v \n", col, val)
		}
	}
	fmt.Println("==> ", count)
}
