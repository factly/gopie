package repositories

type OlapRepository interface {
	Connect() error
	CreateTable(query string) ([][]string, error)
	Query(query string) ([][]string, error)
	DropTable(query string) ([][]string, error)
	Disconnect() error
}
