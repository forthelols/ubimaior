# -*- coding: utf-8 -*-
"""Command line tools to view, query and manipulate hierarchical  configurations."""
import collections
import itertools

import click

import ubimaior
import ubimaior.configurations
import ubimaior.formats


# TODO: Add options to override 'schema' and 'scopes'


@click.group()
@click.option(
    '--configuration', show_default=True, type=click.Path(exists=True, dir_okay=False),
    help='Configuration file for ubimaior.'
)
@click.option(
    '--format', 'fmt', type=click.Choice(ubimaior.formats.FORMATTERS),
    help='Format of the configuration files.'
)
@click.pass_context
def main(ctx, configuration, fmt):
    """Manages hierarchical configuration files"""
    # Set defaults from a configuration file (needed). If the file is not passed from
    # the command line, the default is to iteratively search for .ubimaior.yaml starting from the
    # present working directory and proceeding up to root.
    if not configuration:
        try:
            configuration = ubimaior.configurations.search_file_in_path('.ubimaior.yaml')
        except IOError as exc:
            raise click.ClickException('ubimaior configuration ' + str(exc))

    ctx.ensure_object(dict)
    ctx.obj['configuration'] = configuration
    ubimaior.configurations.setup_from_file(configuration)
    if fmt:
        ctx.obj['format'] = fmt
        ubimaior.configurations.set_default_format(fmt)


@main.command()
@click.option(
    '--validate', type=click.BOOL, default=False, show_default=True, is_flag=True,
    help='Validates the configuration against its schema.'
)
@click.option(
    '--blame', type=click.BOOL, default=False, show_default=True, is_flag=True,
    help='Show provenance of each attribute or value in the configuration.'
)
@click.argument('name')
def show(validate, blame, name):
    """Display the merged configuration files."""
    cfg = ubimaior.load(name)
    settings = ubimaior.configurations.retrieve_settings()
    if validate:
        schema = settings['schema']
        if not schema:
            raise click.ClickException('validation schema not found')
        ubimaior.configurations.validate(cfg, schema)

    formatter = ubimaior.formats.FORMATTERS[settings.format]
    styles = collections.defaultdict(lambda: lambda x: click.style(x, bold=True))
    styles[ubimaior.formats.TokenTypes.ATTRIBUTE] = lambda x: click.style(x, fg='yellow', bold=True)

    cfg_lines, provenance = formatter.pprint(cfg, formatters=styles)

    if blame:
        scopes = format_provenance(provenance)
        formatted_cfg_str = [p + line for p, line in zip(scopes, cfg_lines)]
        formatted_cfg_str = '\n'.join(formatted_cfg_str)
    else:
        formatted_cfg_str = '\n'.join(x for x in cfg_lines)

    click.echo_via_pager(formatted_cfg_str)


def format_provenance(provenance):
    """Format the provenance in a form that is ready to be displayed.

    Args:
        provenance (list): list of scopes

    Returns:
        list of formatted string (one for each provenance item)
    """
    # Construct a color map for the scopes
    colors = ['red', 'green', 'blue', 'magenta', 'cyan', 'white', 'black']
    items = sorted(set(itertools.chain.from_iterable(provenance)))
    color_map = dict(zip(items, colors))

    # Style all the scopes according to the colormap
    scopes = [
        click.style('[[', bold=True) +
        ','.join(click.style(x, fg=color_map[x]) for x in scope) +
        click.style(']]', bold=True) + '    '
        for scope in provenance
    ]

    raw_lengths = [len(','.join(x)) for x in provenance]
    max_width = max(raw_lengths)
    spaces_to_add = [max_width - x for x in raw_lengths]
    return [val + ' '*spacer for val, spacer in zip(scopes, spaces_to_add)]
