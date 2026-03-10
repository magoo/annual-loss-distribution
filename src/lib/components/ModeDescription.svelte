<script>
  let {
    activeSection,
    activeDistType = 'lognormal',
    scenarioActive = false,
  } = $props();

  const description = $derived.by(() => {
    const bySection = activeSection === 'frequency'
      ? {
          lognormal: 'Choose Lognormal when you expect most years to be manageable, but some years to be noticeably worse. It fits a \"usually normal, sometimes spiky\" incident pattern.',
          pert: 'Choose PERT when you can give a low, likely, and high estimate for yearly incidents. It stays within that range and leans toward your \"most likely\" estimate.',
          pareto: 'Choose Pareto when rare blow-up years are a serious concern. It puts more emphasis on extreme incident counts than the other options.',
          scenario: 'Scenario Mode uses the scenarios below to run 10,000 simulated years. In each year, it decides which scenarios happen and how often, then totals incidents across scenarios.',
        }
      : {
          lognormal: 'Choose Lognormal when most incidents cost around a typical amount, but a few are much more expensive. It is a good default for \"common losses plus occasional surprises.\"',
          pert: 'Choose PERT when you can estimate a best case, most likely case, and worst case cost per incident. It stays in that range and favors the middle estimate.',
          pareto: 'Choose Pareto when a few incidents could be extraordinarily expensive. It is designed for situations where extreme losses drive risk.',
          scenario: 'Scenario Mode uses the scenarios below to run 10,000 simulated years. It samples incident counts and costs from those scenario assumptions to build the cost distribution.',
        };

    const key = scenarioActive ? 'scenario' : activeDistType;
    return bySection[key] ?? bySection.lognormal;
  });
</script>

<div class="mode-description" role="note" aria-live="polite">
  <p>{description}</p>
</div>

<style>
  .mode-description {
    padding-top: var(--spacing-1);
  }

  .mode-description p {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    line-height: 1.6;
    margin: 0;
  }
</style>
