<?php
/**
 * Static factuality spectrum (methodology). Replaces the DS island.
 *
 * @package InkBytes
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

$ib_fact = array(
	array( 'high',  'High',  94, 'Corroborated across many independent outlets; claims trace cleanly to source.' ),
	array( 'mixed', 'Mixed', 61, 'Still developing — outlets diverge on specifics; we flag what isn\'t settled.' ),
	array( 'low',   'Low',   28, 'Thin or disputed sourcing. Rarely published; never from a single source.' ),
);
?>
<div class="fact-grid">
  <?php foreach ( $ib_fact as $f ) : ?>
    <div class="fact-card">
      <div class="fact-card-top">
        <span class="dsx-fact dsx-fact--<?php echo esc_attr( $f[0] ); ?>"><span class="dsx-fact-dot"></span><?php echo esc_html( $f[1] ); ?> <span class="dsx-fact-score"><?php echo (int) $f[2]; ?></span></span>
        <span class="dsx-bar dsx-bar--<?php echo esc_attr( $f[0] ); ?>"><span class="dsx-bar-fill" style="width:<?php echo (int) $f[2]; ?>%"></span></span>
      </div>
      <p><?php echo esc_html( $f[3] ); ?></p>
    </div>
  <?php endforeach; ?>
</div>
