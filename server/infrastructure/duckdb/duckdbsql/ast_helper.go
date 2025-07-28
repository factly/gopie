package duckdbsql

import "encoding/json"

type astNode map[string]any

const (
	astKeyError        string = "error"
	astKeyErrorMessage string = "error_message"
	astKeyStatements   string = "statements"
	astKeyNode         string = "node"
	astKeyType         string = "type"
	astKeyValue        string = "value"
	astKeyModifiers    string = "modifiers"
	astKeyLimit        string = "limit"
	astKeyOffset       string = "offset"
	astKeyClass        string = "class"
	astKeyID           string = "id"
	astKeyLeft         string = "left"
	astKeyRight        string = "right"
	astKeyCTE          string = "cte_map"
	astKeyPosition     string = "position"
)

func toBoolean(a astNode, k string) bool {
	v, ok := a[k]
	if !ok {
		return false
	}
	val, _ := v.(bool)
	return val
}

func toString(a astNode, k string) string {
	v, ok := a[k]
	if !ok {
		return ""
	}
	s, _ := v.(string)
	return s
}

func toNode(a astNode, k string) astNode {
	v, ok := a[k]
	if !ok {
		return nil
	}
	n, _ := v.(map[string]any)
	return n
}

func toArray(a astNode, k string) []any {
	v, ok := a[k]
	if !ok {
		return make([]any, 0)
	}
	arr, _ := v.([]any)
	return arr
}

func toNodeArray(a astNode, k string) []astNode {
	arr := toArray(a, k)
	nodeArr := make([]astNode, len(arr))
	for i, e := range arr {
		nodeArr[i] = e.(map[string]any)
	}
	return nodeArr
}

func forceConvertToNum[N int32 | int64 | uint32 | uint64 | float32 | float64](v any) N {
	switch vt := v.(type) {
	case int:
		return N(vt)
	case int32:
		return N(vt)
	case int64:
		return N(vt)
	case float32:
		return N(vt)
	case float64:
		return N(vt)
	case json.Number:
		i, err := vt.Int64()
		if err == nil {
			return N(i)
		}
		f, err := vt.Float64()
		if err == nil {
			return N(f)
		}
		return 0
	}
	return 0
}
