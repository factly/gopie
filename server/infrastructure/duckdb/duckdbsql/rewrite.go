package duckdbsql

import (
	"encoding/json"
	"fmt"
)

func (sn *selectNode) rewriteLimit(limit, offset int) error {
	modifiersNode := toNodeArray(sn.ast, astKeyModifiers)
	var limitModifier astNode

	for _, mod := range modifiersNode {
		if toString(mod, astKeyType) == "LIMIT_MODIFIER" {
			limitModifier = mod
			break
		}
	}

	if limitModifier == nil {
		newModifier, err := createLimitModifier(limit, offset)
		if err != nil {
			return err
		}
		if _, ok := sn.ast[astKeyModifiers]; !ok {
			sn.ast[astKeyModifiers] = make([]any, 0)
		}
		sn.ast[astKeyModifiers] = append(sn.ast[astKeyModifiers].([]any), newModifier)
		return nil
	}

	existingLimitNode := toNode(limitModifier, astKeyLimit)
	existingOffsetNode := toNode(limitModifier, astKeyOffset)

	shouldUpdateLimit := false
	if existingLimitNode == nil {
		shouldUpdateLimit = true
	} else {
		valueNode := toNode(existingLimitNode, astKeyValue)
		if valueNode != nil {
			existingLimitVal := forceConvertToNum[int64](valueNode[astKeyValue])
			if existingLimitVal == 0 || int64(limit) < existingLimitVal {
				shouldUpdateLimit = true
			}
		} else {
			shouldUpdateLimit = true
		}
	}

	if shouldUpdateLimit {
		newLimitObject, err := createConstantLimit(limit)
		if err != nil {
			return err
		}
		limitModifier[astKeyLimit] = newLimitObject
	}

	if existingOffsetNode == nil && offset > 0 {
		newOffsetObject, err := createConstantLimit(offset)
		if err != nil {
			return err
		}
		limitModifier[astKeyOffset] = newOffsetObject
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
