{pkgs, lib, config, inputs, ... }:
{
  packages = with pkgs; [
    nixd
    gcc
    gnumake
    cmake

    llvmPackages.clang-tools
    compiledb
  ];

  languages.python = {
     enable = true;
     package = pkgs.python311;
     venv.enable = true;
     libraries = with pkgs; [
       stdenv.cc.cc.lib
       zlib
       libGL
       glib
     ];
     venv.requirements = ''
       numpy
       matplotlib

       xarray
       netcdf4
       dask
       requests
     '';
   };
}