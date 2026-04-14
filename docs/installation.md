# Installation

## Stable release

To install thanos, run this command in your terminal:

```sh
uv add thanos-cli
```

Or with `pipx` (recommended for CLI tools — installs in an isolated environment):

```sh
pipx install thanos-cli
```

Or if you prefer to use `pip`:

```sh
pip install thanos-cli
```

## From source

The source files for thanos can be downloaded from the [Github repo](https://github.com/soldatov-ss/thanos).

You can either clone the public repository:

```sh
git clone git://github.com/soldatov-ss/thanos
```

Or download the [tarball](https://github.com/soldatov-ss/thanos/tarball/master):

```sh
curl -OJL https://github.com/soldatov-ss/thanos/tarball/master
```

Once you have a copy of the source, you can install it with:

```sh
cd thanos
uv pip install .
```
