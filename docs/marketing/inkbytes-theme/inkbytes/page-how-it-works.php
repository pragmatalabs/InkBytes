<?php
/**
 * How it works — generated from site/how-it-works.html by build-templates.py.
 * Re-run the script after editing the source HTML, or edit here directly.
 *
 * @package InkBytes
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }
get_header();
?>
<main>

  <section class="page-hero page-hero--accent">
    <div class="wrap">
      <span class="kicker"><span class="pulse"></span> How it works</span>
      <h1>A pipeline, <span class="accent">not a chatbot</span>.</h1>
      <p class="lead">Five stages turn the open web's firehose into one trustworthy page — and a hard rule sits at the center: nothing publishes without at least two independent sources agreeing it's a story.</p>
    </div>
  </section>

  <section class="section--tight">
    <div class="wrap">
      <div class="trust-list">
        <div class="trust-row">
          <div class="trust-row-label"><span class="num">01</span>Collect</div>
          <div>
            <h3>Harvest the open web, in real time</h3>
            <p>We read many trusted outlets in parallel — homepages and RSS/Atom feeds — across English and Spanish. A strict freshness window keeps only current stories, so stale archive content never floats to the top.</p>
          </div>
        </div>
        <div class="trust-row">
          <div class="trust-row-label"><span class="num">02</span>Enrich</div>
          <div>
            <h3>Tag the who, what and where</h3>
            <p>Each article is tagged with the people, organizations and places it mentions, plus its topic and language, and condensed into a short summary the rest of the pipeline can reason over.</p>
          </div>
        </div>
        <div class="trust-row">
          <div class="trust-row-label"><span class="num">03</span>Cluster</div>
          <div>
            <h3>Group by meaning, not keywords</h3>
            <p>Articles are grouped by semantic similarity plus shared entities — not matching words — so different outlets covering the same event land together even when they phrase it nothing alike.</p>
          </div>
        </div>
        <div class="trust-row">
          <div class="trust-row-label"><span class="num">04</span>Synthesize</div>
          <div>
            <h3>One balanced, cited page</h3>
            <p>Once a cluster has at least two distinct sources, we write a single balanced, source-traceable page. Every claim carries a citation back to the reporting it came from.</p>
          </div>
        </div>
        <div class="trust-row">
          <div class="trust-row-label"><span class="num">05</span>Verify</div>
          <div>
            <h3>Drop anything that can't be traced</h3>
            <p>A quality-assurance pass removes any claim that can't be tied back to a real source, and validates each page before it goes live.</p>
          </div>
        </div>
      </div>

      <div class="cards-row c2" style="margin-top:30px">
        <div class="callout">
          <span class="rule-chip" style="align-self:flex-start">≥ 2 sources</span>
          <div>
            <h3>The two-source rule</h3>
            <p>Single-source rumors never become an InkBytes page. If only one outlet has it, we wait until it's independently corroborated.</p>
          </div>
        </div>
        <div class="callout" style="border-left-color:var(--ink-3)">
          <span class="icon-badge"><svg class="uicon" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9.5"/><line x1="5.5" y1="5.5" x2="18.5" y2="18.5"/></svg></span>
          <div>
            <h3>What we don't do</h3>
            <p>No original reporting. No opinion dressed as fact. No engagement-maximizing feed. We aggregate and synthesize — and we say so.</p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="section band center">
    <div class="wrap measure">
      <h2 class="h-sec" style="margin:0 auto 18px">See the pipeline's output.</h2>
      <p class="lead" style="margin:0 auto 30px">Open any event and follow each claim back to the reporting it came from.</p>
      <a class="ib-btn v-primary sz-lg" href="https://inkbytes.org">Start reading — $9/mo</a>
    </div>
  </section>

</main>
<?php
get_footer();
