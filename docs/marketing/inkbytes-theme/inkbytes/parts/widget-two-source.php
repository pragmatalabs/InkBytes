<?php
/**
 * Static two-source proof (methodology). Replaces the DS island.
 *
 * @package InkBytes
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }
?>
<div class="twosrc">
  <span class="dsx-stack">
    <?php
    foreach ( array( 'reuters', 'ap', 'bloomberg', 'guardian', 'ft', 'cnbc' ) as $o ) {
      echo ib_outlet_logo( $o ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
    }
    ?>
    <span class="dsx-logo dsx-logo--more" title="1 more">+1</span>
  </span>
  <span class="dsx-cov"><?php echo ib_sparkline(); // phpcs:ignore ?><span class="dsx-cov-num">247</span> articles · peak <b>Today</b></span>
</div>
