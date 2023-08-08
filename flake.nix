{
  description = "Small python script to load bitwarden-store ssh keys into ssh-agent";

  outputs = inputs@{ nixpkgs, flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [
        inputs.flake-parts.flakeModules.easyOverlay
      ];
      systems = [ "x86_64-linux" "aarch64-darwin" ];
      perSystem = { config, self', inputs', pkgs, system, ... }:
        let
          package = pkgs.python3Packages.buildPythonPackage {
            pname = "bitwarden-ssh-agent";
            version = "0.1.2";
            src = ./. ;
            propagatedBuildInputs = [ pkgs.python3Packages.setuptools pkgs.bitwarden-cli ];
            format = "other";
            installPhase = ''
              mkdir -p $out/bin/
              mv bw_add_sshkeys.py $out/bin/bitwarden-ssh-agent
              chmod +x $out/bin/bitwarden-ssh-agent
            '';
            meta = with pkgs.lib; {
              description = "Small python script to load bitwarden-store ssh keys into ssh-agent";
              homepage = "https://github.com/joaojacome/bitwarden-ssh-agent";
              license = licenses.mit;
            };
          };
        in {
          overlayAttrs = {
            bitwarden-ssh-agent = package;
          };
          packages.default = package;
          devShells.default = pkgs.mkShell {
            packages = [
              pkgs.bitwarden-cli
              (pkgs.python3.withPackages(pkgs: [
                  pkgs.setuptools
              ]))
            ];
          };
        };
      };
}
