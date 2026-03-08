import click


@click.command()
@click.option("--seed", default=None, help="RNG seed for reproducibility")
def main(seed: str | None) -> None:
    """Poker Coach — AI-powered No Limit Hold'em training."""
    click.echo("Poker Coach starting...")


if __name__ == "__main__":
    main()
