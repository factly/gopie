package duckdbsql

import (
	"encoding/json"
	"fmt"
)

func (sn *selectNode) rewriteLimit(limit, offset int) error {
	modifiersNode := toNodeArray(sn.ast, astKeyModifiers)
	updated := false
	for _, v := range modifiersNode {
		if toString(v, astKeyType) != "LIMIT_MODIFIER" {
			continue
		}

		// Always update the limit value
		limitObject, err := createConstantLimit(limit)
		if err != nil {
			return err
		}
		v[astKeyLimit] = limitObject

		// Add or update the offset value if it's greater than 0
		if offset > 0 {
			offsetObject, err := createConstantLimit(offset)
			if err != nil {
				return err
			}
			v[astKeyOffset] = offsetObject
		} else {
			// Ensure offset is set to null if not provided
			v[astKeyOffset] = nil
		}

		updated = true
	}

	if !updated {
		// If no limit modifier existed, create a new one
		v, err := createLimitModifier(limit, offset)
		if err != nil {
			return err
		}
		sn.ast[astKeyModifiers] = append(sn.ast[astKeyModifiers].([]any), v)
	}

	return nil
}

func createConstantLimit(limit int) (astNode, error) {
	var n astNode
	err := json.Unmarshal(fmt.Appendf(nil, `
    {
       "class":"CONSTANT",
       "type":"VALUE_CONSTANT",
       "alias":"",
       "value":{
          "type":{
             "id":"INTEGER",
             "type_info":null
          },
          "is_null":false,
          "value":%d
       }
    }
`, limit), &n)
	return n, err
}

func createLimitModifier(limit, offset int) (astNode, error) {
	var n astNode
	err := json.Unmarshal([]byte(`
{
    "type":"LIMIT_MODIFIER",
    "limit": null,
    "offset": null
}
`), &n)
	if err != nil {
		return nil, err
	}

	// Create and set the limit object
	limitObject, err := createConstantLimit(limit)
	if err != nil {
		return nil, err
	}
	n[astKeyLimit] = limitObject

	// If offset is provided, create and set the offset object
	if offset > 0 {
		offsetObject, err := createConstantLimit(offset)
		if err != nil {
			return nil, err
		}
		n[astKeyOffset] = offsetObject
	}

	return n, nil
}
