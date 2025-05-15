package duckdb

import (
	"fmt"

	pg_query "github.com/pganalyze/pg_query_go/v6"
	"vitess.io/vitess/go/vt/sqlparser"
)

// walkAndQualifyUnqualifiedTablesForPg recursively traverses relevant parts of a SELECT statement's AST
// and sets the provided schemaName for any table reference (RangeVar) that is not already schema-qualified.
//
// Args:
//
//	node: The current AST node to process.
//	schemaName: The schema name to apply to unqualified table references.
//
// WARN: This function, in its current simplified form, may not correctly distinguish
// between base tables and references to Common Table Expressions (CTEs).
// If a CTE reference appears as a RangeVar with an empty Schemaname,
// this function might attempt to qualify it, which is generally not the desired behavior for CTEs.
func walkAndQualifyUnqualifiedTablesForPg(node *pg_query.Node, schemaName string) {
	if node == nil {
		return
	}

	// Case 1: Direct table reference (RangeVar)
	if rv := node.GetRangeVar(); rv != nil {
		// Only apply the schemaName if the table reference (RangeVar)
		// does not already have an explicit schema.
		// This prevents overwriting existing qualifications like "other_schema.my_table".
		if rv.Schemaname == "" {
			// Add a check here if you need to distinguish CTEs or other special RangeVar uses.
			// For example, RangeVars for CTEs should not be schema-qualified.
			// This basic version applies the schema if it's currently empty.
			fmt.Printf("SELECT context: Qualifying unqualified table '%s' with schema '%s'\n", rv.Relname, schemaName)
			rv.Schemaname = schemaName
		}
		// rv.Relname (the table's name within its schema) remains unchanged.
		return // Processed this RangeVar node.
	}

	// Case 2: Join expression
	if joinExpr := node.GetJoinExpr(); joinExpr != nil {
		walkAndQualifyUnqualifiedTablesForPg(joinExpr.Larg, schemaName)
		walkAndQualifyUnqualifiedTablesForPg(joinExpr.Rarg, schemaName)
		walkAndQualifyUnqualifiedTablesForPg(joinExpr.Quals, schemaName) // Join condition
		return
	}

	// Case 3: The SELECT statement itself
	if selStmtPayload := node.GetSelectStmt(); selStmtPayload != nil {
		// FROM clause
		if selStmtPayload.FromClause != nil {
			for _, fromItemNode := range selStmtPayload.FromClause {
				walkAndQualifyUnqualifiedTablesForPg(fromItemNode, schemaName)
			}
		}
		// WHERE clause
		if selStmtPayload.WhereClause != nil {
			walkAndQualifyUnqualifiedTablesForPg(selStmtPayload.WhereClause, schemaName)
		}
		// Target list (SELECTed expressions)
		if selStmtPayload.TargetList != nil {
			for _, targetItemNode := range selStmtPayload.TargetList {
				if resTarget := targetItemNode.GetResTarget(); resTarget != nil {
					// Recurse on the value of the result target, which can be an expression
					walkAndQualifyUnqualifiedTablesForPg(resTarget.Val, schemaName)
				}
			}
		}
		// WITH clause (Common Table Expressions)
		if withClause := selStmtPayload.GetWithClause(); withClause != nil {
			if withClause.Ctes != nil {
				for _, cteItemNode := range withClause.Ctes {
					if commonTableExpr := cteItemNode.GetCommonTableExpr(); commonTableExpr != nil {
						// The query defining the CTE must also be processed.
						if commonTableExpr.Ctequery != nil {
							walkAndQualifyUnqualifiedTablesForPg(commonTableExpr.Ctequery, schemaName)
						}
					}
				}
			}
		}
		// HAVING clause
		if selStmtPayload.HavingClause != nil {
			walkAndQualifyUnqualifiedTablesForPg(selStmtPayload.HavingClause, schemaName)
		}

		// For UNION, INTERSECT, EXCEPT (Set Operations)
		if selStmtPayload.Larg != nil {
			// Larg and Rarg are *pg_query.SelectStmt, so wrap them in a Node for recursion
			largNode := &pg_query.Node{Node: &pg_query.Node_SelectStmt{SelectStmt: selStmtPayload.Larg}}
			walkAndQualifyUnqualifiedTablesForPg(largNode, schemaName)
		}
		if selStmtPayload.Rarg != nil {
			rargNode := &pg_query.Node{Node: &pg_query.Node_SelectStmt{SelectStmt: selStmtPayload.Rarg}}
			walkAndQualifyUnqualifiedTablesForPg(rargNode, schemaName)
		}
		return
	}

	// Case 4: SubLink (subquery in an expression)
	if subLink := node.GetSubLink(); subLink != nil {
		walkAndQualifyUnqualifiedTablesForPg(subLink.Subselect, schemaName)
		if subLink.Testexpr != nil { // For subqueries used with ANY, ALL, EXISTS, etc.
			walkAndQualifyUnqualifiedTablesForPg(subLink.Testexpr, schemaName)
		}
		return
	}

	// Case 5: General expressions (A_Expr for arithmetic/comparison, BoolExpr for AND/OR/NOT)
	if aExpr := node.GetAExpr(); aExpr != nil {
		walkAndQualifyUnqualifiedTablesForPg(aExpr.Lexpr, schemaName)
		walkAndQualifyUnqualifiedTablesForPg(aExpr.Rexpr, schemaName)
		return
	}
	if boolExpr := node.GetBoolExpr(); boolExpr != nil {
		if boolExpr.Args != nil {
			for _, argItemNode := range boolExpr.Args {
				walkAndQualifyUnqualifiedTablesForPg(argItemNode, schemaName)
			}
		}
		return
	}
	// Function calls
	if funcCall := node.GetFuncCall(); funcCall != nil {
		// Arguments to the function
		if funcCall.Args != nil {
			for _, argItemNode := range funcCall.Args {
				walkAndQualifyUnqualifiedTablesForPg(argItemNode, schemaName)
			}
		}
		// Window definition (OVER clause)
		if funcCall.Over != nil { // funcCall.Over is *pg_query.WindowDef
			if funcCall.Over.PartitionClause != nil {
				for _, partItemNode := range funcCall.Over.PartitionClause {
					walkAndQualifyUnqualifiedTablesForPg(partItemNode, schemaName)
				}
			}
			if funcCall.Over.OrderClause != nil {
				for _, orderItemNode := range funcCall.Over.OrderClause { // Each is a Node, typically SortBy
					if sortBy := orderItemNode.GetSortBy(); sortBy != nil {
						walkAndQualifyUnqualifiedTablesForPg(sortBy.Node, schemaName)
					} else {
						// Fallback if it's not a SortBy node but some other expression
						walkAndQualifyUnqualifiedTablesForPg(orderItemNode, schemaName)
					}
				}
			}
			if funcCall.Over.StartOffset != nil {
				walkAndQualifyUnqualifiedTablesForPg(funcCall.Over.StartOffset, schemaName)
			}
			if funcCall.Over.EndOffset != nil {
				walkAndQualifyUnqualifiedTablesForPg(funcCall.Over.EndOffset, schemaName)
			}
		}
		return
	}

	// Case 6: A WindowDef node itself (e.g., from a WINDOW clause)
	if windowDef := node.GetWindowDef(); windowDef != nil {
		if windowDef.PartitionClause != nil {
			for _, partItemNode := range windowDef.PartitionClause {
				walkAndQualifyUnqualifiedTablesForPg(partItemNode, schemaName)
			}
		}
		if windowDef.OrderClause != nil {
			for _, orderItemNode := range windowDef.OrderClause { // Each is a Node, typically SortBy
				if sortBy := orderItemNode.GetSortBy(); sortBy != nil {
					walkAndQualifyUnqualifiedTablesForPg(sortBy.Node, schemaName)
				} else {
					walkAndQualifyUnqualifiedTablesForPg(orderItemNode, schemaName)
				}
			}
		}
		if windowDef.StartOffset != nil {
			walkAndQualifyUnqualifiedTablesForPg(windowDef.StartOffset, schemaName)
		}
		if windowDef.EndOffset != nil {
			walkAndQualifyUnqualifiedTablesForPg(windowDef.EndOffset, schemaName)
		}
		return
	}

	// Case 7: A list of nodes (generic list, e.g., arguments to some operators)
	if listNode := node.GetList(); listNode != nil {
		for _, itemNode := range listNode.Items {
			walkAndQualifyUnqualifiedTablesForPg(itemNode, schemaName)
		}
		return
	}

	// Case 8: ResTarget (an item in the SELECT list, e.g., "column_name AS alias" or "expr AS alias")
	if resTarget := node.GetResTarget(); resTarget != nil {
		// resTarget.Name is the alias (optional).
		// resTarget.Val is the expression being selected. Recurse into the expression.
		walkAndQualifyUnqualifiedTablesForPg(resTarget.Val, schemaName)
		return
	}
}

// mysqlQualifierWalker holds the schema name to apply.
// It's used as the context for the visitor function during AST traversal.
type mysqlQualifierWalker struct {
	schemaName string
}

// newMySQLQualifierWalker creates a new walker with the given schema name.
func newMySQLQualifierWalker(schemaName string) *mysqlQualifierWalker {
	return &mysqlQualifierWalker{
		schemaName: schemaName,
	}
}

// qualifyUnqualifiedTableNode is the core visitor function called by sqlparser.Walk.
// It inspects each node in the AST. If a node represents an unqualified table
// in a FROM or JOIN clause, it applies the default schemaName.
func (w *mysqlQualifierWalker) qualifyUnqualifiedTableNode(node sqlparser.SQLNode) (kontinue bool, err error) {
	switch n := node.(type) {
	case *sqlparser.AliasedTableExpr:
		if tableName, ok := n.Expr.(*sqlparser.TableName); ok {
			if tableName.Qualifier.IsEmpty() {
				fmt.Printf("MySQL context: Qualifying unqualified table '%s' with schema '%s'\n",
					tableName.Name.String(), w.schemaName)
				tableName.Qualifier = sqlparser.NewIdentifierCS(w.schemaName)
			}
		}
	}
	return true, nil // Continue traversal to children
}

// WalkAndQualifyUnqualifiedTablesForMySQL recursively traverses relevant parts of a MySQL statement's AST
// (parsed by github.com/vitessio/vitess/go/vt/sqlparser) and sets the provided schemaName
// for any table reference (TableName within an AliasedTableExpr) that is not already schema-qualified.
//
// Args:
//
//	stmtNode: The root AST node of the parsed SQL statement (e.g., *sqlparser.Select, *sqlparser.Insert).
//	schemaName: The schema name to apply to unqualified table references.
//
// Note: This function, similar to the provided PostgreSQL example, may not perfectly
// distinguish between base tables and references to Common Table Expressions (CTEs)
// without more sophisticated scope tracking. If a CTE reference appears as a TableName
// with an empty Qualifier, this function might attempt to qualify it.
func WalkAndQualifyUnqualifiedTablesForMySQL(stmtNode sqlparser.SQLNode, schemaName string) error {
	if stmtNode == nil {
		return nil
	}

	walker := newMySQLQualifierWalker(schemaName)

	// sqlparser.Walk traverses the AST. For each node, it calls the provided
	// visitor function (walker.qualifyUnqualifiedTableNode).
	// Modifications made by the visitor are applied to the AST in place.
	err := sqlparser.Walk(walker.qualifyUnqualifiedTableNode, stmtNode)
	if err != nil {
		return fmt.Errorf("error walking MySQL AST for table qualification: %w", err)
	}

	return nil
}
