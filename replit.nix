{ pkgs }:
{
  deps = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.git
    pkgs.chromium
    pkgs.chromedriver
    pkgs.nodejs_20
  ];
}