{ pkgs, lib, config, inputs, ... }:

let
  x11AndGpuLibs = with pkgs; [
    stdenv.cc.cc.lib
    zlib
    glib
    libGL
    libGLU
    freeglut
    glew
    glfw
    xorg.libX11
    xorg.libXt
    xorg.libXext
    xorg.libXrender
    xorg.libXrandr
    xorg.libXinerama
    xorg.libXcursor
    xorg.libXi
    xorg.libXfixes
    xorg.libXdamage
    xorg.libXxf86vm
    xorg.libSM
    xorg.libICE
    fontconfig
    freetype
  ];
in {
  packages = with pkgs; [
    nixd
    gcc
    gnumake
    cmake
    llvmPackages.clang-tools
    compiledb
    cudaPackages.cudatoolkit
  ] ++ x11AndGpuLibs;

  languages.python = {
    enable = true;
    package = pkgs.python311;
    venv.enable = true;
    # Важно: именно этот список пробрасывается в LD_LIBRARY_PATH для pip-колес (VTK/PyVista)
    libraries = x11AndGpuLibs;
    venv.requirements = ''
      numpy
      matplotlib
      xarray
      netcdf4
      h5netcdf
      h5py
      dask
      requests
      earthaccess
      streamlit
      plotly
      pyvista
    '';
  };
}