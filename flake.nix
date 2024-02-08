{
  description = "A Python application defined as a Nix Flake";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    nix-filter.url = "github:numtide/nix-filter";
    openapi-checks = {
      url = "github:openeduhub/nix-openapi-checks";
      inputs = {
        flake-utils.follows = "flake-utils";
      };
    };
    data-utils = {
      url = "github:openeduhub/data-utils";
      inputs = {
        flake-utils.follows = "flake-utils";
        nixpkgs.follows = "nixpkgs";
      };
    };
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    let
      nix-filter = self.inputs.nix-filter.lib;

      ### create the python installation for the package
      python-packages-build = py-pkgs:
        with py-pkgs; [
          setuptools
          # data manipulation
          numpy
          pandas
          data-utils
          # webservice
          uvicorn
          pydantic
          fastapi
        ];

      ### create the python installation for development
      # the development installation contains all build packages,
      # plus some additional ones we do not need to include in production.
      python-packages-devel = py-pkgs:
        with py-pkgs; [
          black
          ipython
          isort
          mypy
          pyflakes
          pylint
          pytest
          pytest-cov
        ]
        ++ (python-packages-build py-pkgs);

      ### the python package and application
      get-python-package = py-pkgs: py-pkgs.buildPythonPackage {
        pname = "topic-statistics";
        version = "0.1.0";
        /* only include files that are related to the application.
               this will prevent unnecessary rebuilds */
        src = nix-filter {
          root = self;
          include = [
            # folders
            "topic_statistics"
            "test"
            # files
            ./setup.py
            ./requirements.txt
          ];
          exclude = [ (nix-filter.matchExt "pyc") ];
        };
        propagatedBuildInputs = (python-packages-build py-pkgs);
      };

      get-python-app = py-pkgs: py-pkgs.toPythonApplication (
        get-python-package py-pkgs
      );

    in
    {
      lib = {
        default = get-python-package;
      };
      # define an overlay to the library to nixpkgs
      overlays.default = (final: prev: {
        pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
          (python-final: python-prev: {
            topic-statistics = self.outputs.lib.default python-final;
          })
        ];
      });
    } //
    flake-utils.lib.eachDefaultSystem
      (system:
        let
          pkgs = nixpkgs.legacyPackages.${system}.extend
            self.inputs.data-utils.overlays.default;
          python = pkgs.python3;
          python-app = get-python-app python.pkgs;
        in
        {
          # the packages that we can build
          packages = {
            default = python-app;
          };
          # the development environment
          devShells.default = pkgs.mkShell {
            buildInputs = [
              # the development installation of python
              (python.withPackages python-packages-devel)
              # python lsp server
              pkgs.nodePackages.pyright
              # for automatically generating nix expressions, e.g. from PyPi
              pkgs.nix-template
              pkgs.nix-init
            ];
          };
        }
      );
}
