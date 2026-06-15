<?php
/**
 * Front page — the InkBytes marketing landing page.
 *
 * @package InkBytes
 */

get_header();
$reader = esc_url( inkbytes_reader_url() );
?>

<main id="top">

  <!-- HERO -->
  <section class="hero">
    <div class="wrap">
      <span class="eyebrow"><span class="pulse"></span> Ad-free · Multi-source · Citation-traceable</span>
      <h1 class="serif">One page <span class="accent">worth twenty.</span></h1>
      <p class="sub">The news is fragmented, noisy, and biased. InkBytes reads many trusted sources for you and synthesizes <strong>one elegant, balanced page per event</strong> — with every fact traceable to its source. Pay to skip the noise.</p>
      <div class="cta-row">
        <a class="btn btn-primary btn-lg" href="<?php echo $reader; ?>">Start reading — $9/mo</a>
        <a class="btn btn-ghost btn-lg" href="#how">See how it works</a>
      </div>
      <p class="micro">No ads. No algorithmic feed. Cancel anytime.</p>

      <!-- event mock -->
      <div class="mock">
        <div class="mock-top">
          <span class="dot"></span><span class="dot"></span><span class="dot"></span>
          <span class="mock-url">inkbytes.org / event</span>
        </div>
        <div class="mock-body">
          <span class="mock-tag">World · Synthesized from 6 sources</span>
          <h2 class="mock-h" style="text-align:left;margin-top:8px">Central banks signal a coordinated shift as inflation cools across markets</h2>
          <div class="mock-meta"><span>● Updated 2h ago</span><span>● 6 outlets</span><span>● Factuality 0.94</span><span>● EN · ES</span></div>
          <div class="chips"><span class="chip">Federal Reserve</span><span class="chip">ECB</span><span class="chip">Inflation</span><span class="chip">Markets</span></div>
          <p class="mock-p">Policymakers across major economies converged this week on a more dovish tone, with three central banks hinting at rate adjustments as price pressures ease…</p>
          <div class="src">Sources: <b>Reuters</b> · <b>AP</b> · <b>Bloomberg</b> · <b>El País</b> · +2 — <span style="color:var(--accent-dot);font-weight:600">every claim cited</span></div>
        </div>
      </div>
    </div>
  </section>

  <!-- PROBLEM -->
  <section class="band" id="problem">
    <div class="wrap">
      <p class="kicker">The problem</p>
      <h2>Twenty tabs. Twenty slants. No clear picture.</h2>
      <p class="lead">Every outlet shows a different slice of the same event. The volume makes the full story impossible to assemble — and telling fact from fiction keeps getting harder.</p>
      <div class="grid3">
        <div class="card"><span class="ico">🧩</span><h3>Fragmented</h3><p>The same event is scattered across dozens of outlets, each with a partial view.</p></div>
        <div class="card"><span class="ico">📢</span><h3>Noisy</h3><p>Endless headlines, ads, and clickbait bury the handful of facts that actually matter.</p></div>
        <div class="card"><span class="ico">⚖️</span><h3>Biased</h3><p>Algorithmic feeds and editorial slant decide what you see — and what you don't.</p></div>
      </div>
    </div>
  </section>

  <!-- HOW IT WORKS -->
  <section id="how">
    <div class="wrap">
      <p class="kicker">How it works</p>
      <h2>A reproducible pipeline, not a wrapper over a chatbot.</h2>
      <p class="lead">Five stages turn the firehose of the open web into one trustworthy page — with a hard rule: <strong>nothing publishes without at least two independent sources.</strong></p>
      <div class="steps">
        <div class="step"><div class="n">1</div><h3>Collect</h3><p>Harvest many trusted outlets in parallel, in real time.</p></div>
        <div class="step"><div class="n">2</div><h3>Enrich</h3><p>Tag entities, topic and language; summarize each article.</p></div>
        <div class="step"><div class="n">3</div><h3>Cluster</h3><p>Group articles on the same event by meaning, not keywords.</p></div>
        <div class="step"><div class="n">4</div><h3>Synthesize</h3><p>Write one balanced page once ≥2 sources agree it's a story.</p></div>
        <div class="step"><div class="n">5</div><h3>Verify</h3><p>A QA pass drops any claim not tied back to a real source.</p></div>
      </div>
    </div>
  </section>

  <!-- WHY / COMPARE -->
  <section class="band" id="why">
    <div class="wrap">
      <p class="kicker">Why InkBytes</p>
      <h2>The gap between aggregators, chatbots, and reading it all yourself.</h2>
      <p class="lead">Static aggregators add no synthesis. General chatbots hallucinate and can't be reproduced. Reading ten sources by hand doesn't scale. InkBytes is the missing middle.</p>
      <div style="overflow-x:auto">
      <table class="tbl">
        <thead><tr><th></th><th>Synthesizes one page</th><th>Citation-traceable</th><th>Multi-source by design</th><th>Ad-free</th></tr></thead>
        <tbody>
          <tr><td class="ink-col">InkBytes</td><td><span class="yes">✓</span></td><td><span class="yes">✓</span></td><td><span class="yes">✓ ≥2 sources</span></td><td><span class="yes">✓</span></td></tr>
          <tr><td>Google / Apple News</td><td><span class="no">— links only</span></td><td><span class="no">—</span></td><td><span class="no">—</span></td><td><span class="no">— ads</span></td></tr>
          <tr><td>Feedly / Inoreader</td><td><span class="no">—</span></td><td><span class="no">—</span></td><td><span class="no">—</span></td><td><span class="yes">✓</span></td></tr>
          <tr><td>Ground News</td><td><span class="no">— bias labels</span></td><td><span class="yes">✓</span></td><td><span class="yes">✓</span></td><td><span class="no">— tiers</span></td></tr>
          <tr><td>ChatGPT / Perplexity</td><td><span class="yes">✓</span></td><td><span class="no">~ inconsistent</span></td><td><span class="no">~ varies</span></td><td><span class="yes">✓</span></td></tr>
        </tbody>
      </table>
      </div>
    </div>
  </section>

  <!-- FEATURES -->
  <section id="features">
    <div class="wrap">
      <p class="kicker">What you get</p>
      <h2>Built for people who need the whole story.</h2>
      <div class="grid2" style="margin-top:8px">
        <div class="feat"><div class="fi">🔗</div><div><h3>Every claim cited</h3><p>An evidence rail links each statement back to the original reporting. It isn't magic — it's traceable aggregation.</p></div></div>
        <div class="feat"><div class="fi">🕸️</div><div><h3>Entity context</h3><p>People, organizations and places are extracted and linked, so you can follow a story across events.</p></div></div>
        <div class="feat"><div class="fi">🌎</div><div><h3>Bilingual coverage</h3><p>Global English plus LATAM Spanish — one balanced account across languages and borders.</p></div></div>
        <div class="feat"><div class="fi">🚫</div><div><h3>No ads, no feed games</h3><p>You're the reader, not the product. No tracking-driven feed deciding what you should think.</p></div></div>
        <div class="feat"><div class="fi">📲</div><div><h3>Installable app</h3><p>Add InkBytes to your home screen. Fast, clean, and built for daily reading.</p></div></div>
        <div class="feat"><div class="fi">🤖</div><div><h3>Ask the corpus</h3><p>A built-in assistant answers questions grounded only in published, cited events — no made-up facts.</p></div></div>
      </div>
    </div>
  </section>

  <!-- PRICING -->
  <section class="band" id="pricing">
    <div class="wrap">
      <p class="kicker">Pricing</p>
      <h2>One simple plan. Skip the noise.</h2>
      <p class="lead">Headlines are free. The full synthesis, evidence rail, and entity links are for members.</p>
      <div class="price-wrap">
        <div class="plan">
          <h3>Free</h3>
          <div class="amt">$0</div>
          <ul>
            <li>Headlines &amp; first ~100 words</li>
            <li>Browse every event</li>
            <li class="off">Full synthesized page</li>
            <li class="off">Evidence rail &amp; citations</li>
            <li class="off">Entity links &amp; assistant</li>
          </ul>
          <a class="btn btn-ghost" href="<?php echo $reader; ?>" style="border-color:#fff3;color:#fff">Browse free</a>
        </div>
        <div class="plan pro">
          <span class="badge">Most popular</span>
          <h3>Member</h3>
          <div class="amt">$9<small> / month</small></div>
          <ul>
            <li>Everything in Free</li>
            <li>Full multi-source synthesis</li>
            <li>Complete evidence rail &amp; citations</li>
            <li>Entity context &amp; related events</li>
            <li>Corpus assistant &amp; installable app</li>
          </ul>
          <a class="btn btn-primary" href="<?php echo $reader; ?>">Start reading</a>
        </div>
      </div>
    </div>
  </section>

  <!-- AUDIENCE -->
  <section id="audience">
    <div class="wrap">
      <p class="kicker">Who it's for</p>
      <h2>For anyone who can't afford to miss the full picture.</h2>
      <div class="aud">
        <span>Executives &amp; analysts</span><span>Journalists &amp; researchers</span>
        <span>Professionals staying current</span><span>Academics &amp; students</span>
        <span>The informed citizen</span>
      </div>
    </div>
  </section>

  <!-- FINAL CTA -->
  <section class="band final">
    <div class="wrap">
      <h2 style="margin-bottom:18px">Your source for comprehensive news.</h2>
      <p>Stop assembling the story from twenty tabs. Read the one page that already did it — with the receipts.</p>
      <a class="btn btn-primary btn-lg" href="<?php echo $reader; ?>">Start reading — $9/mo</a>
    </div>
  </section>

</main>

<?php
get_footer();
