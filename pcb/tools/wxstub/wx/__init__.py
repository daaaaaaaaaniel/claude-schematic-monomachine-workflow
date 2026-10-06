"""Stand-in for wxPython, used only by tools/separate.sh when the real one can't be imported (Ubuntu 24.04 with
Python 3.13 as python3: the distro's wxPython is built for 3.12). KiKit only imports wx to fake a GUI app, and on a
machine with no display it does nothing more, so an empty module is enough for `kikit separate`."""
