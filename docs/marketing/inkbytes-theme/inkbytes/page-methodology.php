<?php
/**
 * Methodology & Trust — generated from site/methodology.html by build-templates.py.
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
      <span class="kicker"><span class="pulse"></span> Methodology &amp; Trust</span>
      <h1>It isn't magic. It's <span class="accent">traceable aggregation</span>.</h1>
      <p class="lead">Where our news comes from, the rule that sits at the center, and how we keep ourselves honest. For a news product, this is the page that matters most.</p>
    </div>
  </section>

  <section class="section">
    <div class="wrap">
      <div class="cards-row c2" style="align-items:stretch">
        <div class="card">
          <span class="kicker" style="margin-bottom:14px">The rule at the center</span>
          <h3 style="font-family:var(--font-serif);font-weight:500;font-size:26px;letter-spacing:-.01em;margin-bottom:10px">Nothing publishes without ≥ 2 independent sources.</h3>
          <p style="margin-bottom:22px">Single-source rumors never become an InkBytes page. Once a cluster has at least two distinct sources agreeing it's a story, we synthesize one balanced account — and only then.</p>
          <?php get_template_part( 'parts/widget', 'two-source' ); ?>
        </div>
        <div class="card">
          <span class="kicker" style="margin-bottom:14px">Every page is scored</span>
          <h3 style="font-family:var(--font-serif);font-weight:500;font-size:26px;letter-spacing:-.01em;margin-bottom:18px">Factuality, in the open.</h3>
          <?php get_template_part( 'parts/widget', 'fact-spectrum' ); ?>
        </div>
      </div>
    </div>
  </section>

  <section class="section--tight">
    <div class="wrap">
      <div class="trust-list">
        <div class="trust-row">
          <div class="trust-row-label"><span class="num">01</span>Sources</div>
          <div>
            <h3>Where our information comes from</h3>
            <p>We aggregate and synthesize public reporting from established outlets across English and Spanish, and we link to every source on each page. We do not do original reporting — and we say so.</p>
          </div>
        </div>
        <div class="trust-row">
          <div class="trust-row-label"><span class="num">02</span>The rule</div>
          <div>
            <h3>The ≥ 2-source rule</h3>
            <p>No page is published from a single source. If only one outlet has a story, we wait until it is independently corroborated. This is the single most important safeguard against rumor and error.</p>
          </div>
        </div>
        <div class="trust-row">
          <div class="trust-row-label"><span class="num">03</span>Accuracy</div>
          <div>
            <h3>How we avoid making things up</h3>
            <p>Synthesis is constrained to the clustered source articles — a quality-assurance pass drops any claim that can't be tied back to a source before a page goes live. The corpus assistant answers only from published, cited events.</p>
          </div>
        </div>
        <div class="trust-row">
          <div class="trust-row-label"><span class="num">04</span>Bias</div>
          <div>
            <h3>Balanced, not slant-washed</h3>
            <p>We preserve source diversity and synthesize a balanced account rather than picking a side. There is no engagement-optimizing feed deciding what you should see.</p>
          </div>
        </div>
        <div class="trust-row">
          <div class="trust-row-label"><span class="num">05</span>Freshness</div>
          <div>
            <h3>No stale news resurfacing</h3>
            <p>Strict freshness windows keep archived or stale content from floating back to the top as if it were new.</p>
          </div>
        </div>
        <div class="trust-row">
          <div class="trust-row-label"><span class="num">06</span>Corrections</div>
          <div>
            <h3>Accountability in the open</h3>
            <p>Errors are corrected openly and noted on the page. If you spot something wrong, tell us — corrections are part of the product, not an embarrassment to hide.</p>
          </div>
        </div>
        <div class="trust-row">
          <div class="trust-row-label"><span class="num">07</span>Limitations</div>
          <div>
            <h3>What we can't do (yet)</h3>
            <p>Synthesis can lag a breaking event, and coverage depends on which outlets we harvest. We list our source outlets and are honest about the edges of our coverage.</p>
          </div>
        </div>
        <div class="trust-row">
          <div class="trust-row-label"><span class="num">08</span>Coverage</div>
          <div>
            <h3>Languages &amp; regions</h3>
            <p>The current vertical is LATAM bilingual — Dominican Republic, Mexico, Colombia, Argentina and more — plus global English business and technology coverage. Spanish is first-class, not a machine translation.</p>
          </div>
        </div>
      </div>

      <div class="callout" style="margin-top:30px">
        <span class="icon-badge"><svg class="uicon" viewBox="0 0 24 24"><path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg></span>
        <div>
          <h3>Found an error? Report a correction.</h3>
          <p>We fix mistakes in the open. Send the page and what's wrong, and we'll note the correction on the event itself. <a href="/contact/" style="color:var(--accent);border-bottom:1px solid var(--accent-soft)">Report a correction →</a></p>
        </div>
      </div>
    </div>
  </section>

  <section class="section band center">
    <div class="wrap measure">
      <h2 class="h-sec" style="margin:0 auto 18px">Trust you can check.</h2>
      <p class="lead" style="margin:0 auto 30px">Open any page, follow any claim to its source, and see the factuality score for yourself.</p>
      <a class="ib-btn v-primary sz-lg" href="https://inkbytes.org">Start reading — $9/mo</a>
    </div>
  </section>

</main>
<?php
get_footer();
