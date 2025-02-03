{
  description = "Gopie dev environment";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = f: nixpkgs.lib.genAttrs supportedSystems (system: f system);
    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = pkgs.mkShell {
            name = "gopie-dev";
            packages = with pkgs; [
              go
              gopls
              delve
              air
              duckdb
              sqlc
              go-tools
              golangci-lint
              gotests
              jq
              goose
            ];
            shellHook = ''
              export GOPATH="$HOME/go"
              export PATH="$GOPATH/bin:$PATH"
              
              if [ -f config.env ]; then
                source config.env
              fi
              echo "Welcome to Gopie Development Environment"
              echo "Available Commands:"
              echo "  air        - Start development server with live reload"
              echo "  go test    - Run tests"
              echo "  sqlc generate - Generate database code"
              echo "Note: Configure MOTHERDUCK_TOKEN in config.env file"
            '';
          };
        });
    };
}
