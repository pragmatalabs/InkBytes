<?php
/**
 * Footer.
 *
 * @package InkBytes
 */
?>
<footer>
  <div class="wrap foot">
    <a class="brand" href="<?php echo esc_url( home_url( '/' ) ); ?>"><svg><use href="#ink"/></svg>InkBytes</a>
    <div class="foot-links">
      <a href="#how">How it works</a><a href="#why">Why InkBytes</a><a href="#pricing">Pricing</a>
    </div>
    <span>© <?php echo esc_html( wp_date( 'Y' ) ); ?> InkBytes · Accuracy · Transparency · Accountability</span>
  </div>
</footer>
<?php wp_footer(); ?>
</body>
</html>
