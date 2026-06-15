<?php
/**
 * About — generated from site/about.html by build-templates.py.
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
      <span class="kicker"><span class="pulse"></span> About InkBytes</span>
      <h1>A paid, ad-free reader for people who need the <span class="accent">whole story</span>.</h1>
      <p class="lead">Each event — a real-world development covered by many outlets — gets one elegant, source-cited page. You get the substance without the noise.</p>
    </div>
  </section>

  <section class="section--tight">
    <div class="wrap measure">
      <div class="prose dropcap">
        <p>InkBytes is a paid, ad-free news reader. Each <strong>event</strong> — a real-world development covered by multiple outlets — gets one elegant, source-cited page.</p>
        <p>We read many sources, group the articles about the same story, and synthesize them into a short, cited brief. You get the substance without the noise. No ads. No tracking. No sponsored content. One flat monthly fee.</p>
        <p><strong>Why we built it.</strong> The news is fragmented, noisy, and biased. Getting a balanced account of an important event meant opening twenty tabs and reconciling twenty slants yourself. InkBytes does that work — and shows its receipts.</p>
      </div>
    </div>
  </section>

  <section class="section band center" style="position:relative;overflow:hidden">
    <div class="mark-ghost" style="width:300px;height:300px;top:-50px;right:-40px"><img src="<?php echo esc_url( get_theme_file_uri( 'assets/illustrations/reporter.svg' ) ); ?>" alt="" style="filter:invert(1)" /></div>
    <div class="wrap" style="position:relative">
      <p class="pullquote">“It isn't magic — it's traceable aggregation. We aggregate and synthesize; we don't pretend to do original reporting.”<span class="pullquote-cite">The InkBytes principle</span></p>
    </div>
  </section>

  <section class="section">
    <div class="wrap">
      <div class="sec-head center">
        <span class="kicker">What we stand for</span>
        <h2 class="h-sec">Three values, applied to every page.</h2>
      </div>
      <div class="cards-row c3">
        <div class="card">
          <span class="icon-badge"><svg class="uicon" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="3.5"/></svg></span>
          <h3>Accuracy</h3>
          <p>Every fact is traceable to its source. Automated quality checks run on every page, with review where it applies.</p>
        </div>
        <div class="card">
          <span class="icon-badge"><svg class="uicon" viewBox="0 0 24 24"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg></span>
          <h3>Transparency</h3>
          <p>The sources behind each page are visible. Open any claim and you can see exactly where it came from.</p>
        </div>
        <div class="card">
          <span class="icon-badge"><svg class="uicon" viewBox="0 0 24 24"><path d="M3 12a9 9 0 1 0 3-6.7"/><polyline points="3 3 3 8 8 8"/></svg></span>
          <h3>Accountability</h3>
          <p>Errors are corrected in the open, and the system learns from its failures rather than burying them.</p>
        </div>
      </div>
    </div>
  </section>

  <section class="section band">
    <div class="wrap">
      <div class="sec-head center">
        <span class="kicker">Lineage</span>
        <h2 class="h-sec">From InkPills to InkBytes.</h2>
        <p class="lead">The same idea — consolidated “pills” of information synthesized from many sources, each referencing its origins — now a formalized pipeline, and a name we could ship.</p>
      </div>
      <div class="lineage">
        <div class="lineage-node">
          <div class="yr">2023</div>
          <div class="nm serif">InkPills</div>
        </div>
        <div class="lineage-arrow">→</div>
        <div class="lineage-node now">
          <div class="yr">Today</div>
          <div class="nm serif">InkBytes</div>
        </div>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="wrap measure center">
      <span class="kicker kicker--muted" style="justify-content:center">Made in the Dominican Republic · LATAM + global English</span>
      <div class="founder" style="margin-top:30px">
        <div class="founder-portrait"><svg class="uicon" viewBox="0 0 24 24" style="width:48px;height:48px"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg></div>
        <div>
          <div class="founder-name serif">Julián De La Rosa</div>
          <div class="founder-role">Founder · A Pragmata Labs venture</div>
        </div>
      </div>
    </div>
  </section>

  <section class="section band center">
    <div class="wrap measure">
      <h2 class="h-sec" style="margin:0 auto 18px">Read the one page that already did the work.</h2>
      <p class="lead" style="margin:0 auto 30px">Browse every event free. Become a member to unlock the full synthesis, citations, and entity context.</p>
      <a class="ib-btn v-primary sz-lg" href="https://inkbytes.org">Start reading — $9/mo</a>
    </div>
  </section>

</main>
<?php
get_footer();
