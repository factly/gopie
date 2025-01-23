package motherduck

import (
	"database/sql"
	"fmt"

	"github.com/factly/gopie/application/repositories"
	"github.com/factly/gopie/domain/models"
	"github.com/factly/gopie/domain/pkg/config"
	"github.com/factly/gopie/domain/pkg/logger"
	_ "github.com/marcboeker/go-duckdb"
	"go.uber.org/zap"
)

type motherDuckOlapoDriver struct {
	db     *sql.DB
	logger *logger.Logger
}

func NewMotherDuckOlapoDriver(cfg *config.MotherDuckConfig, logger *logger.Logger) (repositories.OlapRepository, error) {
	olap := motherDuckOlapoDriver{
		logger: logger,
	}
	logger.Info("connecting to motherduck")
	fmt.Println("connecting to motherduck")
	err := olap.Connect(cfg)
	if err != nil {
		logger.Error("error connecting to motherduck", zap.Error(err))
		fmt.Println("error connecting to motherduck: ", err.Error())
		return nil, err
	}
	logger.Info("connected to motherduck")
	fmt.Println("connected to motherduck")
	return &olap, nil
}

func (m *motherDuckOlapoDriver) Connect(cfg *config.MotherDuckConfig) error {
	dsn := fmt.Sprintf("md:%s?motherduck_token=%s", cfg.DBName, cfg.Token)
	db, err := sql.Open("duckdb", dsn)
	if err != nil {
		m.logger.Error("error connecting to motherduck", zap.Error(err))
		return err
	}

	m.db = db
	return nil
}

func (m *motherDuckOlapoDriver) Close() error {
	if m.db != nil {
		return m.db.Close()
	}
	return nil
}

func (m *motherDuckOlapoDriver) CreateTable(filePath, tableName, format string) error {
	createSql := ""
	switch format {
	case "parquet":
		createSql = fmt.Sprintf("select * from read_parquet('%s')", filePath)
		break
	case "csv":
		createSql = fmt.Sprintf("select * from read_csv('%s')", filePath)
		break
	case "json":
		createSql = fmt.Sprintf("select * read_json('%s')", filePath)
		break
	default:
		return fmt.Errorf("unsupported format: %s", format)
	}
	fmt.Println("createSql: ", createSql)
	fmt.Println("tableName: ", tableName)

	sql := fmt.Sprintf(`CREATE OR REPLACE TABLE "%s" AS (%s)`, tableName, createSql)

	_, err := m.db.Exec(sql)

	return err
}

func (m *motherDuckOlapoDriver) Query(query string) (*models.Result, error) {
	rows, err := m.db.Query(query)
	if err != nil {
		m.logger.Error("error querying motherduck", zap.Error(err))
		return nil, err
	}

	result := models.Result{
		Rows: rows,
	}

	return &result, nil
}

func (m *motherDuckOlapoDriver) DropTable(tableName string) error {
	sql := fmt.Sprintf("DROP TABLE %s", tableName)

	_, err := m.db.Exec(sql)

	return err
}
