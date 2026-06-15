<?php
/**
 * The Desk (index) — generated from site/desk.html by build-templates.py.
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
      <span class="kicker"><span class="pulse"></span> The Desk</span>
      <h1>Cited analysis. No ads. <span class="accent">Corrections in the open.</span></h1>
      <p class="lead">Daily and weekly columns, methodology notes, and product dispatches — every external claim cited, grounded in that day's published events.</p>
    </div>
  </section>

  <section class="section--tight">
    <div class="wrap">
      <div class="theme-bar" id="themeBar">
        <button class="theme-chip is-active" data-filter="all">All</button>
        <button class="theme-chip" data-filter="politics">Politics</button>
        <button class="theme-chip" data-filter="world">World</button>
        <button class="theme-chip" data-filter="business">Business</button>
        <button class="theme-chip" data-filter="technology">Technology</button>
        <button class="theme-chip" data-filter="culture">Culture</button>
        <button class="theme-chip" data-filter="methodology">Methodology</button>
      </div>

      <!-- Featured -->
      <a class="desk-feature" href="/desk/rate-cuts/">
        <div class="desk-feature-art">
          <img src="<?php echo esc_url( get_theme_file_uri( 'assets/illustrations/strategy-news.svg' ) ); ?>" alt="" />
        </div>
        <div class="desk-feature-body">
          <span class="post-kick">Markets<span class="sep">·</span><span class="date">Jun 3, 2026</span></span>
          <h2>The rate-cut chorus is real — the coordination is mostly coincidence</h2>
          <p class="dek">Three central banks moved toward easing in the same week. Read across twenty outlets, the “coordinated shift” looks less like a plan and more like the same data landing everywhere at once.</p>
          <div class="post-meta" style="border:none;padding-top:0">
            <span class="by">By The Markets Desk</span>
            <span class="post-cited" style="margin-left:auto">14 sources cited</span>
          </div>
        </div>
      </a>

      <!-- Grid -->
      <div class="desk-grid" id="deskGrid">
        <a class="post-card" href="#" data-theme="world">
          <span class="mark-tile"><img src="<?php echo esc_url( get_theme_file_uri( 'assets/illustrations/world-news.svg' ) ); ?>" alt="" /></span>
          <span class="post-kick">World<span class="sep">·</span><span class="date">Jun 2, 2026</span></span>
          <h3>Ceasefire talks stall as both capitals harden their terms</h3>
          <p class="dek">What changed this week, what didn't, and where the eleven outlets covering it actually disagree.</p>
          <div class="post-meta"><span class="by">By The World Desk</span><span class="post-cited" style="margin-left:auto">Cited</span></div>
        </a>
        <a class="post-card" href="#" data-theme="methodology">
          <span class="mark-tile"><img src="<?php echo esc_url( get_theme_file_uri( 'assets/illustrations/newspaper.svg' ) ); ?>" alt="" /></span>
          <span class="post-kick">Methodology<span class="sep">·</span><span class="date">Jun 1, 2026</span></span>
          <h3>How we cluster articles by meaning, not keywords</h3>
          <p class="dek">Why two stories about the same event land together even when they share almost no words.</p>
          <div class="post-meta"><span class="by">By The Methodology Desk</span><span class="post-cited" style="margin-left:auto">Cited</span></div>
        </a>
        <a class="post-card" href="#" data-theme="technology">
          <span class="mark-tile"><img src="<?php echo esc_url( get_theme_file_uri( 'assets/illustrations/broadcasting.svg' ) ); ?>" alt="" /></span>
          <span class="post-kick">Dispatch<span class="sep">·</span><span class="date">May 30, 2026</span></span>
          <h3>Three new outlets joined the corpus this week</h3>
          <p class="dek">A short, dated note on what we added, why, and how it widens coverage.</p>
          <div class="post-meta"><span class="by">By The Desk</span><span class="post-cited" style="margin-left:auto">Dispatch</span></div>
        </a>
        <a class="post-card" href="#" data-theme="politics">
          <span class="mark-tile"><img src="<?php echo esc_url( get_theme_file_uri( 'assets/illustrations/announcement.svg' ) ); ?>" alt="" /></span>
          <span class="post-kick">Politics<span class="sep">·</span><span class="date">May 29, 2026</span></span>
          <h3>Reading a noisy election week across twenty outlets</h3>
          <p class="dek">When every headline contradicts the last, the signal is in what all of them agree on.</p>
          <div class="post-meta"><span class="by">By The Politics Desk</span><span class="post-cited" style="margin-left:auto">Cited</span></div>
        </a>
        <a class="post-card" href="#" data-theme="culture">
          <span class="mark-tile"><img src="<?php echo esc_url( get_theme_file_uri( 'assets/illustrations/magazine.svg' ) ); ?>" alt="" /></span>
          <span class="post-kick">Culture<span class="sep">·</span><span class="date">May 27, 2026</span></span>
          <h3>The festival economy and who it leaves out</h3>
          <p class="dek">A measured look at the numbers behind a record season — and the costs that rarely make the recap.</p>
          <div class="post-meta"><span class="by">By The Culture Desk</span><span class="post-cited" style="margin-left:auto">Cited</span></div>
        </a>
        <a class="post-card" href="#" data-theme="methodology">
          <span class="mark-tile"><img src="<?php echo esc_url( get_theme_file_uri( 'assets/illustrations/reporter.svg' ) ); ?>" alt="" /></span>
          <span class="post-kick">Methodology<span class="sep">·</span><span class="date">May 24, 2026</span></span>
          <h3>Why the ≥ 2-source rule matters more than speed</h3>
          <p class="dek">Being first is cheap. Being right — and able to show it — is the whole product.</p>
          <div class="post-meta"><span class="by">By The Methodology Desk</span><span class="post-cited" style="margin-left:auto">Cited</span></div>
        </a>
      </div>
    </div>
  </section>

  <!-- Editorial standards -->
  <section class="section--tight">
    <div class="wrap">
      <p class="center mono" style="font-size:12px;letter-spacing:.06em;color:var(--muted);text-transform:uppercase">Every external claim is cited · No ads, no sponsored content · Corrections in the open · Byline &amp; date on everything</p>
    </div>
  </section>

  <!-- Content types -->
  <section class="section band">
    <div class="wrap">
      <div class="sec-head center">
        <span class="kicker">What's on The Desk</span>
        <h2 class="h-sec">Three kinds of writing, one standard.</h2>
      </div>
      <div class="cards-row c3">
        <div class="card typecard">
          <span class="mark-tile"><img src="<?php echo esc_url( get_theme_file_uri( 'assets/illustrations/newspaper.svg' ) ); ?>" alt="" /></span>
          <div><h3>Editorial columns</h3><p>Daily and weekly analysis by theme — politics, world, business, technology, culture — grounded in that day's cited events.</p></div>
        </div>
        <div class="card typecard">
          <span class="mark-tile"><img src="<?php echo esc_url( get_theme_file_uri( 'assets/illustrations/strategy-news.svg' ) ); ?>" alt="" /></span>
          <div><h3>Methodology essays</h3><p>Transparency long-reads on how the pipeline actually works — clustering, the ≥2-source rule, keeping the assistant grounded.</p></div>
        </div>
        <div class="card typecard">
          <span class="mark-tile"><img src="<?php echo esc_url( get_theme_file_uri( 'assets/illustrations/announcement.svg' ) ); ?>" alt="" /></span>
          <div><h3>Dispatches</h3><p>Short, dated product updates and periodic transparency reports — new outlets, new features, corrections issued.</p></div>
        </div>
      </div>
    </div>
  </section>

  <section class="section band center" style="padding-top:0">
    <div class="wrap measure">
      <h2 class="h-sec" style="margin:0 auto 18px">Read the events behind the columns.</h2>
      <p class="lead" style="margin:0 auto 30px">Every Desk piece links back to the cited events in the reader. Start there.</p>
      <a class="ib-btn v-primary sz-lg" href="https://inkbytes.org">Start reading — $9/mo</a>
    </div>
  </section>

</main>
<?php
get_footer();
