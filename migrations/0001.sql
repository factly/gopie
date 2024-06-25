-- Create the catalog table based on catalogv2
CREATE TABLE gopie.catalog (
	kind TEXT NOT NULL,
	name TEXT NOT NULL,
	data BLOB NOT NULL,
	created_on TIMESTAMPTZ NOT NULL,
	updated_on TIMESTAMPTZ NOT NULL
);

-- Create the controller_version table and insert the initial version
CREATE TABLE gopie.controller_version (
	version INTEGER NOT NULL
);

INSERT INTO gopie.controller_version (version) VALUES (0);

