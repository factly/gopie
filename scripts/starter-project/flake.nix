{
  description = "A flake for a Python development environment";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };
  outputs = { self, nixpkgs }:
    let
      forAllSystems = nixpkgs.lib.genAttrs [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];

      pkgsFor = system: import nixpkgs {
        inherit system;
      };

    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = pkgsFor system;
          python = pkgs.python311;

          pythonEnv = python.withPackages (ps: [
            ps.requests
            ps.pip         
            ps.virtualenv  
            ps.boto3
          ]);

        in
        {
          default = pkgs.mkShell {
            buildInputs = [
              pythonEnv
            ];

            shellHook = ''
              echo "--- Python Nix Flake Environment ---"
              echo "Python version: $(python --version)"
              echo "Packages available: requests, boto3, pip"
              
              # Automatically create and source a venv directory for pip installs
              if [ ! -d ".venv" ]; then
                echo "Creating virtual environment in ./.venv..."
                python -m venv .venv
              fi

              source .venv/bin/activate
              
              # Set the PYTHONPATH to include packages installed via pip
              export PYTHONPATH="${pythonEnv}/lib/${python.libPrefix}/site-packages:$PYTHONPATH"
              
              echo "Activated virtual environment from ./.venv"
              unset SOURCE_DATE_EPOCH
            '';
          };
        });
    };
}
