# Welcome to Ubimaior

``ubimaior`` is a package to manage hierarchical configurations
split over multiple files and scopes. It's strongly inspired by
the way [Spack](https://spack.io) manages its configuration and
aims at replicating the same user-level mechanism with an API 
that mimics Python built-in objects.

## Getting started

Many applications or libraries are customizable using configuration
files, environment variables or command line arguments. In general
a software can define different places, or _scopes_, where its configuration is 
stored or from where it is retrieved from. 

Usually the semantics is such that configuration set in a higher
scope overrides the one set in a lower scope. ``ubimaior``, instead,
gives the ability to either override or merge options when they are
defined in a dictionary or list.

Consider for instance having rules in your configuration to enable
or disable certain features of your application:
```yaml
config:
  # "enable" is a list of objects defining a list
  # of plugins to enable
  enable:
    - name: plugin1
      options: "foo,fee"
```
and assume that a `config.yaml` file can be stored either at the system
level in `/etc/app`, with higher precedence, or at the user level in 
`~/.app`, with lower precedence. In that case, if we have in `/etc/app/config.yaml`:
```yaml
config:
  enable:
    - name: plugin1
      options: 'foo'
```
and in `~/.app/config.yaml`:
```yaml
config:
  enable:
    - name: plugin2
      options: 'bar,baz'
```
what the application will receive as input configuration will be:
```yaml
config:
  enable:
    - name: plugin1
      options: 'foo'
    - name: plugin2
      options: 'bar,baz'
```
i.e. a merge of the two files with a list / dictionary order that respects priority.

## Use `ubimaior` in your project

Using `ubimaior` in a project is rather simple. The basic functionality
is available through the `ubimaior.load` function.
Let's go back to our previous example and assume we want to load the
configuration split across the two `config.yaml` files in the "system" and "user" scope.
A single call to `ubimaior.load` can do that:

```python
import ubimaior

config = ubimaior.load(
    config_name='config', config_format='yaml',
    scopes=[('system', '/etc/app'), ('user', '~/.app')]
)
```
The name of the config file is determined by the `config_name` and 
the `config_format` arguments. The `scopes` argument instead defines 
the configuration scopes as a `(name, path)` tuple.

The `config` object is an instance of `ubimaior.mapping.OverridableMapping`
and behaves effectively as a built-in dictionary:
```python
assert len(config) == 1
assert len(config['config']['enable']) == 2
```
while the `config['config']['enable']` item is an instance of 
`ubimaior.sequence.MergedSequence` and behaves like a tuple.
For instance, we can add a new key:
```python
config['config']['data_dir'] = './data'
```


To serialize our changes back to disk we need to call:

```python
import ubimaior

ubimaior.dump(
    config.flattened(), config_name='config', config_format='yaml',
    scopes=[('system', '/etc/app'), ('user', '~/.app')]
)
```

## Commands

* `ubimaior show` - Display the merged configuration file.
* `ubimaior -h` - Print help message and exit.

## Project layout

    mkdocs.yml    # Configuration file for docs
    .github/      # Github configuration files
    docs/
        index.md  # The documentation homepage
        ...       # Other markdown pages, images and other files
    tests/        # Unit tests
    ubimaior/     # Code for the package