"""Shared visual language for the notebook and persistent browser editor."""

SHARED_CSS = """

          :root {
            --ald-accent: #4f5fbf;
            --ald-risk-accent: #B42318;
            --ald-rose: #d84b73;
            --ald-ink: var(--foreground, #202534);
            --ald-muted: var(--muted-foreground, #667085);
            --ald-border: color-mix(in srgb, var(--foreground, #202534) 13%, transparent);
            --ald-surface: color-mix(
              in srgb, var(--background, #ffffff) 97%, var(--foreground, #202534) 3%
            );
            --ald-surface-soft: color-mix(
              in srgb, var(--background, #ffffff) 93%, var(--ald-accent) 7%
            );
          }

          .ald-hero,
          .ald-shell,
          .ald-footer {
            box-sizing: border-box;
            margin-inline: auto;
            max-width: 72rem;
            width: 100%;
          }

          .ald-hero {
            padding: clamp(1.25rem, 4vw, 3rem) clamp(.4rem, 2vw, 1rem) 1.25rem;
          }

          .ald-eyebrow,
          .ald-kicker {
            color: var(--ald-risk-accent);
            font-size: .72rem;
            font-weight: 750;
            letter-spacing: .12em;
            text-transform: uppercase;
          }

          .ald-hero h1,
          .ald-step-header h2 {
            color: var(--ald-ink);
            font-family: ui-serif, Georgia, Cambria, "Times New Roman", serif;
            letter-spacing: -.035em;
          }

          .ald-hero h1 {
            font-size: clamp(2rem, 5vw, 3.75rem);
            line-height: 1.02;
            margin: .45rem 0 .7rem;
            max-width: 15ch;
          }

          .ald-hero > p {
            color: var(--ald-muted);
            font-size: clamp(1rem, 2vw, 1.15rem);
            line-height: 1.65;
            margin: 0;
            max-width: 46rem;
          }

          .ald-shell {
            padding: 0 clamp(.35rem, 2vw, 1rem) 2rem;
          }

          .ald-surface {
            background: var(--ald-surface);
            border: 1px solid var(--ald-border);
            border-radius: 12px;
            padding: clamp(.9rem, 2.5vw, 1.35rem);
          }

          .ald-scenario-list,
          .ald-panelist-list {
            display: flex;
            flex-direction: column;
            gap: .8rem;
          }

          .ald-scenario-row,
          .ald-panelist-row {
            align-items: start;
            background: color-mix(
              in srgb, var(--background, #ffffff) 98%, var(--ald-accent) 2%
            );
            border: 1px solid var(--ald-border);
            border-radius: 10px;
            display: grid;
            gap: 1rem;
            padding: 1rem;
          }

          .ald-scenario-row--two-models {
            grid-template-columns:
              minmax(12rem, .85fr) minmax(18rem, 1fr) minmax(18rem, 1fr);
          }

          .ald-scenario-row--with-actions {
            grid-template-columns:
              minmax(12rem, .85fr) minmax(18rem, 1fr) minmax(18rem, 1fr) auto;
          }

          .ald-panelist-row {
            grid-template-columns: minmax(12rem, .8fr) minmax(22rem, 2fr);
          }

          .ald-panelist-row--with-actions {
            grid-template-columns: minmax(12rem, .8fr) minmax(22rem, 2fr) auto;
          }

          .ald-scenario-group,
          .ald-panelist-group {
            min-width: 0;
          }

          .ald-scenario-group-label,
          .ald-panelist-group-label {
            color: var(--ald-muted);
            display: block;
            font-size: .7rem;
            font-weight: 750;
            letter-spacing: .08em;
            margin-bottom: .5rem;
            text-transform: uppercase;
          }

          .ald-scenario-actions,
          .ald-panelist-actions {
            align-self: end;
          }

          .ald-scenario-editor button,
          .ald-panel-editor button {
            white-space: nowrap;
          }

          .ald-toolbar {
            background: var(--ald-surface-soft);
            padding-block: .75rem;
          }

          .ald-toolbar .ald-panel-heading {
            margin-bottom: 0;
            min-width: 0;
          }

          .ald-toolbar .ald-panel-heading span {
            max-width: 16rem;
          }

          .ald-toolbar marimo-radio::part(label),
          .ald-toolbar marimo-slider::part(label) {
            white-space: nowrap;
          }

          .ald-panel-heading {
            margin-bottom: .85rem;
          }

          .ald-panel-heading strong {
            color: var(--ald-ink);
            display: block;
            font-size: .92rem;
          }

          .ald-panel-heading span {
            color: var(--ald-muted);
            display: block;
            font-size: .8rem;
            margin-top: .15rem;
          }

          .ald-step-header {
            border-left: 3px solid var(--ald-risk-accent);
            padding: .1rem 0 .1rem .9rem;
          }

          .ald-step-header h2 {
            font-size: clamp(1.45rem, 3vw, 2rem);
            line-height: 1.15;
            margin: .2rem 0 .35rem;
          }

          .ald-step-header p {
            color: var(--ald-muted);
            line-height: 1.55;
            margin: 0;
            max-width: 52rem;
          }

          .ald-insight {
            background: var(--ald-surface-soft);
            border-left: 3px solid var(--ald-rose);
            border-radius: 8px;
            color: var(--ald-ink);
            line-height: 1.5;
            padding: .75rem .9rem;
          }

          .ald-insight strong {
            color: var(--ald-rose);
            display: block;
            font-size: .7rem;
            letter-spacing: .1em;
            margin-bottom: .2rem;
            text-transform: uppercase;
          }

          .ald-narrative {
            background: var(--ald-surface-soft);
            border: 1px solid var(--ald-border);
            border-radius: 10px;
            padding: .85rem 1rem;
          }

          .ald-narrative h3 {
            color: var(--ald-ink);
            font-family: ui-serif, Georgia, Cambria, "Times New Roman", serif;
            font-size: 1.05rem;
            margin: 0 0 .55rem;
          }

          .ald-narrative ul {
            color: var(--ald-muted);
            margin: 0;
            padding-left: 1.15rem;
          }

          .ald-narrative li + li { margin-top: .35rem; }
          .ald-meta {
            color: var(--ald-muted);
            font-size: .8rem;
            line-height: 1.55;
          }

          .ald-shell :focus-visible {
            outline: 3px solid color-mix(in srgb, var(--ald-accent) 45%, transparent);
            outline-offset: 2px;
          }

          .ald-footer {
            border-top: 1px solid var(--ald-border);
            color: var(--ald-muted);
            font-size: .8rem;
            line-height: 1.55;
            padding: 1rem clamp(.4rem, 2vw, 1rem) 2rem;
          }

          @media (max-width: 80rem) {
            .ald-toolbar > div { flex-wrap: wrap !important; }
            .ald-toolbar > div > div {
              flex: 1 1 calc(50% - .375rem) !important;
              min-width: 0;
            }
            .ald-toolbar marimo-radio::part(label),
            .ald-toolbar marimo-slider::part(label) {
              white-space: normal;
            }
          }

          @media (max-width: 64rem) {
            .ald-scenario-row--two-models,
            .ald-scenario-row--with-actions,
            .ald-panelist-row,
            .ald-panelist-row--with-actions {
              grid-template-columns: 1fr;
            }

            .ald-scenario-actions,
            .ald-panelist-actions {
              justify-self: start;
            }
          }

          @media (max-width: 42rem) {
            .ald-hero { padding-top: 1rem; }
            .ald-hero h1 { max-width: 12ch; }
            .ald-surface { border-radius: 10px; padding: .85rem; }
            .ald-toolbar > div {
              align-items: stretch !important;
              flex-direction: column !important;
            }
            .ald-toolbar > div > div {
              flex: none !important;
              width: 100%;
            }
            .ald-toolbar .ald-panel-heading { min-width: 0; }
          }
        """

HERO_HTML = """

        <div class="ald-hero">
          <span class="ald-eyebrow">Security risk modeling</span>
          <h1>Annual losses from breaches</h1>
          <p>Estimate the frequency and impact of future breaches in dollar values.</p>
        </div>
        """

WORKSPACE_CSS = (
    SHARED_CSS.replace(":root", ":host, .analysis-workspace")
    + """
.analysis-workspace { font: 14px/1.5 ui-sans-serif, system-ui, sans-serif; color: var(--ald-ink); }
.analysis-workspace *, .analysis-workspace *::before, .analysis-workspace *::after { box-sizing: border-box; }
.analysis-workspace [hidden] { display: none !important; }
:where(.analysis-workspace) h2 { font-size: 1.25rem; margin: 0 0 .75rem; }
.analysis-workspace button, .analysis-workspace select, .analysis-workspace input {
  font: inherit; color: inherit; border: 1px solid var(--ald-border); border-radius: 5px;
  background: var(--ald-surface); padding: .4rem .6rem;
}
.analysis-workspace button { cursor: pointer; white-space: nowrap; }
.analysis-workspace button:hover { border-color: var(--ald-accent); }
.analysis-workspace :disabled { cursor: default; opacity: .55; }
.analysis-workspace :focus-visible { outline: 3px solid color-mix(in srgb, var(--ald-accent) 45%, transparent); outline-offset: 2px; }
.analysis-workspace .aw-library { margin-bottom: 1.5rem; }
.analysis-workspace .aw-actions, .analysis-workspace .aw-backups { display: flex; gap: .5rem; align-items: end; flex-wrap: wrap; margin-bottom: .65rem; }
.analysis-workspace .aw-actions select { min-width: 12rem; max-width: 24rem; margin-left: .5rem; }
.analysis-workspace .aw-status { font-weight: 650; }
.analysis-workspace .aw-note { color: var(--ald-muted); font-size: .8rem; }
.analysis-workspace .aw-warning, .analysis-workspace .aw-model-errors { color: var(--ald-risk-accent); }
.analysis-workspace .aw-warning:empty, .analysis-workspace .aw-model-errors:empty, .analysis-workspace .aw-pending:empty { display: none; }
.analysis-workspace .aw-model-errors { padding: .75rem; border: 1px solid var(--ald-border); border-radius: 8px; overflow-wrap: anywhere; }
.analysis-workspace .aw-editor, .analysis-workspace .aw-section, .analysis-workspace .aw-inputs, .analysis-workspace .aw-results { display: flex; flex-direction: column; gap: 1rem; }
.analysis-workspace .aw-section { margin-top: .5rem; }
.analysis-workspace .aw-toolbar { display: grid; grid-template-columns: .95fr 1.35fr 1.75fr 1.6fr; gap: .75rem; align-items: center; }
.analysis-workspace .aw-field { display: flex; flex-direction: column; gap: .25rem; min-width: 0; margin-block: .4rem; }
.analysis-workspace .aw-field > span:first-child, .analysis-workspace legend { font-size: .8rem; font-weight: 600; }
.analysis-workspace .aw-field input, .analysis-workspace .aw-field select { width: 100%; min-width: 0; }
.analysis-workspace .aw-field-error { color: var(--ald-risk-accent); font-size: .75rem; line-height: 1.3; }
.analysis-workspace .aw-field-error:empty { display: none; }
.analysis-workspace input.aw-draft { border-color: #b38313; background: light-dark(#fff9e9, #332c18); }
.analysis-workspace input[aria-invalid=true] { border-color: var(--ald-risk-accent); }
.analysis-workspace .aw-parameters { display: flex; flex-wrap: wrap; gap: .75rem; }
.analysis-workspace .aw-parameters > label { flex: 1 1 8rem; }
.analysis-workspace .aw-radios { border: 0; padding: 0; margin: .4rem 0 .75rem; display: flex; flex-wrap: wrap; gap: .65rem; }
.analysis-workspace .aw-radios legend { margin-bottom: .3rem; }
.analysis-workspace .aw-radios label { display: flex; gap: .3rem; align-items: center; }
.analysis-workspace .aw-radios input { accent-color: var(--ald-accent); }
.analysis-workspace input[type=range] { padding-inline: 0; accent-color: var(--ald-accent); }
.analysis-workspace .ald-panel-editor > button, .analysis-workspace .ald-scenario-editor > button { margin-top: .8rem; }
.analysis-workspace .aw-panel-analytics { overflow: auto; margin-top: .75rem; }
.analysis-workspace table { width: 100%; border-collapse: collapse; font-size: .8rem; }
.analysis-workspace th, .analysis-workspace td { padding: .35rem .5rem; text-align: right; border-bottom: 1px solid var(--ald-border); }
.analysis-workspace th:first-child, .analysis-workspace td:first-child { text-align: left; }
.analysis-workspace .aw-chart { width: 100%; min-width: 0; }
.analysis-workspace .aw-primary { background: #19734a; color: white; width: 100%; margin-top: .5rem; }
.analysis-workspace .aw-stats { display: flex; justify-content: space-around; gap: 1rem; flex-wrap: wrap; text-align: center; }
.analysis-workspace .aw-stats strong { display: block; font-size: 2rem; font-family: ui-serif, Georgia, serif; }
.analysis-workspace .ald-report-card { display: flex; align-items: start; gap: 1rem; }
.analysis-workspace details { flex: 1; min-width: 0; }
.analysis-workspace summary { cursor: pointer; font-weight: 650; }
.analysis-workspace .aw-report { font: inherit; font-size: .85rem; white-space: pre-wrap; overflow-wrap: anywhere; }
@media (max-width: 850px) { .analysis-workspace .aw-toolbar { grid-template-columns: 1fr 1fr; } }
@media (max-width: 550px) { .analysis-workspace .aw-toolbar { grid-template-columns: 1fr; } .analysis-workspace .aw-actions select { width: 100%; max-width: 100%; margin-left: 0; } }
"""
)
