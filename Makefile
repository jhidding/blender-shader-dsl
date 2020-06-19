.PHONY: install

blender_version := $(shell blender --version | head -n1 | cut -d' ' -f2 | cut -d. -f1-2)
target := $(HOME)/.config/blender/$(blender_version)/scripts/addons
source := shader_dsl.py

install: $(target)/shader_dsl.py

$(target)/%: %
	install $< $(target)

