package pkg

// import "github.com/mitchellh/mapstructure"
//
// type ExtractPolicy struct {
// 	RowsStrategy   ExtractPolicyStrategy
// 	RowsLimitBytes uint64
// 	FilesStrategy  ExtractPolicyStrategy
// 	FilesLimit     uint64
// }
//
// type ExtractPolicyStrategy int
//
// const (
// 	ExtractPolicyStrategyUnSpecified ExtractPolicyStrategy = 0
// 	ExtractPolicyHead                ExtractPolicyStrategy = 1
// 	ExtractPolicyTail                ExtractPolicyStrategy = 2
// )
//
// func (s ExtractPolicyStrategy) String() string {
// 	switch s {
// 	case ExtractPolicyHead:
// 		return "head"
// 	case ExtractPolicyTail:
// 		return "tail"
// 	default:
// 		return "unspecified"
// 	}
// }
// func parseStrategy(s string) (Extract)
//
// type rawExtracatPolicy struct {
// 	Rows *struct {
// 		Strategy string `mapstructure:"strategy"`
// 		Size     string `mapstructure:"size"`
// 	} `mapstructure:"rows"`
// 	Files *struct {
// 		Strategy string `mapstructure:"strategy"`
// 		Size     string `mapstructure:"size"`
// 	} `mapstructure:"files"`
// }
//
// func ParseExtractPolicy(cfg map[string]any) (*ExtractPolicy, error) {
// 	if len(cfg) == 0 {
// 		return nil, nil
// 	}
//
// 	raw := &rawExtracatPolicy{}
// 	if err := mapstructure.WeakDecode(cfg, raw); err != nil {
// 		return nil, err
// 	}
//
// 	res := &ExtractPolicy{}
// 	if
// 	if raw.Files != nil {
// 		strategy, err := parse
// 	}
// }
