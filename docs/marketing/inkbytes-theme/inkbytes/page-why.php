<?php
/**
 * Why InkBytes — generated from site/why.html by build-templates.py.
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
      <span class="kicker"><span class="pulse"></span> Why InkBytes</span>
      <h1>The <span class="accent">missing middle</span>.</h1>
      <p class="lead">Static aggregators add no synthesis. General chatbots hallucinate and can't be reproduced. Reading ten sources by hand doesn't scale. InkBytes is the synthesis you can trust — because you can check it.</p>
    </div>
  </section>

  <section class="section band">
    <div class="wrap">
      <div class="ctable-wrap">
        <table class="ctable">
          <thead>
            <tr><th></th><th>Synthesizes one page</th><th>Citation-traceable</th><th>Multi-source by design</th><th>Ad-free</th></tr>
          </thead>
          <tbody>
            <tr class="row-ink"><td>InkBytes</td><td><span class="yes">Yes</span></td><td><span class="yes">Yes</span></td><td><span class="yes">≥ 2 sources</span></td><td><span class="yes">Yes</span></td></tr>
            <tr><td>Google / Apple News</td><td><span class="no">Links only</span></td><td><span class="no">No</span></td><td><span class="no">No</span></td><td><span class="no">Ad-funded</span></td></tr>
            <tr><td>Feedly / Inoreader</td><td><span class="no">No</span></td><td><span class="no">No</span></td><td><span class="no">No</span></td><td><span class="yes">Yes</span></td></tr>
            <tr><td>Ground News</td><td><span class="no">Bias labels</span></td><td><span class="yes">Yes</span></td><td><span class="yes">Yes</span></td><td><span class="partial">Tiered</span></td></tr>
            <tr><td>ChatGPT / Perplexity</td><td><span class="yes">Yes</span></td><td><span class="partial">Inconsistent</span></td><td><span class="partial">Varies</span></td><td><span class="yes">Yes</span></td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="wrap">
      <div class="sec-head center">
        <span class="kicker">The alternatives, honestly</span>
        <h2 class="h-sec">Each does one thing — and stops there.</h2>
      </div>
      <div class="cards-row c2">
        <div class="card"><h3>Google / Apple News</h3><p>Opaque algorithmic curation. They hand you links, not synthesis, keep you fragmented across tabs, and are funded by ads.</p></div>
        <div class="card"><h3>Feedly / Inoreader</h3><p>RSS aggregation, nothing more. They collect feeds but do no cross-source analysis — the reconciling is still on you.</p></div>
        <div class="card"><h3>Ground News</h3><p>Strong on bias <em>labelling</em>, but it doesn't synthesize a single account — you still read several to understand the event.</p></div>
        <div class="card"><h3>ChatGPT / Perplexity</h3><p>Can summarize, but hallucinates, cites inconsistently, and isn't reproducible — ask twice, get two different answers.</p></div>
        <div class="card"><h3>Reading ten sources yourself</h3><p>The gold standard — and impossible at scale. Nobody opens twenty tabs per event, every day.</p></div>
        <div class="card" style="border-color:var(--accent)"><h3 class="accent">InkBytes</h3><p>A reproducible, traceable pipeline with programmatic QA and a hard ≥2-source rule — not a thin wrapper over an LLM.</p></div>
      </div>
    </div>
  </section>

  <section class="section band center" style="padding-top:0">
    <div class="wrap measure">
      <h2 class="h-sec" style="margin:0 auto 18px">Synthesis you can trust because you can check it.</h2>
      <p class="lead" style="margin:0 auto 30px">Every claim links to its source. Every page shows its factuality. That's the edge.</p>
      <a class="ib-btn v-primary sz-lg" href="https://inkbytes.org">Start reading — $9/mo</a>
    </div>
  </section>

</main>
<?php
get_footer();
