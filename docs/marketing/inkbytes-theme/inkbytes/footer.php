<?php
/**
 * Footer — site footer, foot-bar, privacy-first cookie banner.
 * Server-rendered from assets/chrome.jsx (EN).
 *
 * @package InkBytes
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

$ib_reader = esc_url( inkbytes_reader_url() );
$ib_cols   = array(
	'Product' => array(
		array( 'How it works', ib_url( 'how-it-works' ) ),
		array( 'Why InkBytes', ib_url( 'why' ) ),
		array( 'Features',     ib_url( 'features' ) ),
		array( 'Pricing',      ib_url( 'pricing' ) ),
	),
	'Company' => array(
		array( 'About',    ib_url( 'about' ) ),
		array( 'The Desk', ib_url( 'desk' ) ),
		array( 'Contact',  ib_url( 'contact' ) ),
	),
	'Trust' => array(
		array( 'Methodology', ib_url( 'methodology' ) ),
		array( 'Privacy',     ib_url( 'privacy' ) ),
		array( 'Terms',       ib_url( 'terms' ) ),
	),
);
?>
<footer class="site-footer">
  <div id="ib-footer">
    <div class="wrap foot-inner">
      <div class="foot-brand">
        <a class="brand brand--footer" href="<?php echo esc_url( home_url( '/' ) ); ?>" aria-label="InkBytes home">
          <svg class="brand-mark" width="26" height="26" viewBox="0 0 1024 1024" aria-hidden="true"><use href="#ink"/></svg>
          <span class="brand-word">InkBytes</span>
          <span class="brand-dot"></span>
        </a>
        <p class="foot-tag">Your source for comprehensive news. One elegant page per event — every fact traceable to its source.</p>
        <p class="foot-lang mono">EN · ES  ·  Built in the Dominican Republic</p>
      </div>
      <div class="foot-cols">
        <?php foreach ( $ib_cols as $title => $links ) : ?>
          <div class="foot-col">
            <p class="foot-col-title"><?php echo esc_html( $title ); ?></p>
            <ul>
              <?php foreach ( $links as $l ) : ?>
                <li><a href="<?php echo esc_url( $l[1] ); ?>" class="foot-link"><?php echo esc_html( $l[0] ); ?></a></li>
              <?php endforeach; ?>
            </ul>
          </div>
        <?php endforeach; ?>
        <div class="foot-col foot-col--cta">
          <p class="foot-col-title">The reader</p>
          <p class="foot-reader-note">The product lives at the reader app. Browse free.</p>
          <a class="ib-btn v-primary sz-sm" href="<?php echo $ib_reader; ?>">Start reading</a>
        </div>
      </div>
    </div>
  </div>

  <div id="ib-footbar" class="foot-bar">
    <div class="wrap foot-bar-inner">
      <span>© <?php echo esc_html( wp_date( 'Y' ) ); ?> InkBytes</span>
      <span class="foot-values mono">Accuracy · Transparency · Accountability</span>
      <a href="<?php echo $ib_reader; ?>" class="foot-link">inkbytes.org →</a>
    </div>
  </div>
</footer>

<!-- privacy-first cookie banner (vanilla JS, no tracking) -->
<div id="ib-cookie" class="cookie-banner" role="region" aria-label="Cookie notice" hidden>
  <p class="cookie-text">We use only essential cookies. No tracking, no ad profiles, no sold data.
    <a href="<?php echo esc_url( ib_url( 'privacy' ) ); ?>" class="cookie-link">Privacy</a></p>
  <button type="button" class="ib-btn v-primary sz-sm" id="ib-cookie-ok">Got it</button>
</div>
<script>
(function(){
  try{ if(localStorage.getItem('ib-cookie-ok')==='1') return; }catch(e){}
  var b=document.getElementById('ib-cookie'); if(!b) return;
  b.hidden=false;
  var k=document.getElementById('ib-cookie-ok');
  if(k) k.addEventListener('click',function(){ try{localStorage.setItem('ib-cookie-ok','1');}catch(e){} b.hidden=true; });
})();
</script>

<?php wp_footer(); ?>
</body>
</html>
