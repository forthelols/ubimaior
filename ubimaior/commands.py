# -*- coding: utf-8 -*-
"""Command line tools to view, query and manipulate hierarchical  configurations."""
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
@click.argument('name')
def show(validate, name):
    """Display the merged configuration files."""
    cfg = ubimaior.load(name)
    settings = ubimaior.configurations.retrieve_settings()
    if validate:
        schema = settings['schema']
        if not schema:
            raise click.ClickException('validation schema not found')
        ubimaior.configurations.validate(cfg, schema)

    formatter = ubimaior.formats.FORMATTERS[settings.format]
    cfg_lines, _ = formatter.pprint(cfg)
    click.echo_via_pager('\n'.join(cfg_lines))
