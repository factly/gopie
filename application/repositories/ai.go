package repositories

type AiRepository interface {
	GenerateSql(nl string) (string, error)
}
