<?php
/**
 * Static event-mock (home hero). Replaces the DS-composed React island.
 *
 * @package InkBytes
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }
?>
<div class="evt">
  <div class="evt-top">
    <span class="evt-dot"></span><span class="evt-dot"></span><span class="evt-dot"></span>
    <span class="evt-url mono">inkbytes.org/event/central-banks-coordinated-shift</span>
    <span class="evt-syn mono">Synthesized</span>
  </div>
  <div class="evt-body">
    <div class="evt-kick">
      <span class="kicker">World</span>
      <span class="evt-date mono">Wed, Jun 3, 2026 · 11:40</span>
    </div>
    <h3 class="evt-h serif">Central banks signal a coordinated shift as inflation cools across markets</h3>

    <div class="evt-meta">
      <span class="dsx-fact dsx-fact--high"><span class="dsx-fact-dot"></span>High <span class="dsx-fact-score">94</span></span>
      <span class="dsx-stack">
        <?php
        foreach ( array( 'reuters', 'ap', 'bloomberg', 'guardian', 'ft' ) as $o ) {
          echo ib_outlet_logo( $o ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
        }
        ?>
        <span class="dsx-logo dsx-logo--more" title="2 more">+2</span>
      </span>
      <span class="dsx-cov"><?php echo ib_sparkline(); // phpcs:ignore ?><span class="dsx-cov-num">247</span> articles · peak <b>Today</b></span>
    </div>

    <div class="evt-tags">
      <span class="dsx-tag"><span class="dsx-tag-dot" style="background:var(--entity-org)"></span>Federal Reserve</span>
      <span class="dsx-tag"><span class="dsx-tag-dot" style="background:var(--entity-org)"></span>ECB</span>
      <span class="dsx-tag"><span class="dsx-tag-dot" style="background:var(--entity-person)"></span>Jerome Powell</span>
      <span class="dsx-tag"><span class="dsx-tag-dot" style="background:var(--entity-topic)"></span>Inflation</span>
    </div>

    <p class="evt-p serif">Policymakers across major economies converged this week on a more dovish tone, with three central banks <span class="cited">hinting at rate adjustments as price pressures ease<sup>1</sup></span>. Officials framed the move as coordinated rather than reactive, citing softer core inflation prints across the euro area and the United States.</p>

    <div class="evt-rail">
      <span class="evt-rail-label mono">Sources</span>
      <span class="evt-rail-logos">
        <?php
        foreach ( array( 'reuters', 'ap', 'bloomberg', 'ft', 'guardian' ) as $o ) {
          echo ib_outlet_logo( $o ); // phpcs:ignore
        }
        ?>
      </span>
      <span class="evt-rail-cite">+2 · <b>every claim cited</b></span>
    </div>
  </div>
</div>
