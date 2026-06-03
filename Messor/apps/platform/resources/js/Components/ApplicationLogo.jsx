export default function ApplicationLogo(props) {
    // InkBytes / Messor mark: a rounded "chip" with two text lines —
    // a news/ink-byte motif. The outer fill comes from props (brand blue);
    // the inner lines stay white.
    return (
        <svg
            {...props}
            viewBox="0 0 32 32"
            xmlns="http://www.w3.org/2000/svg"
        >
            <rect x="2" y="2" width="28" height="28" rx="7" />
            <rect x="8" y="10.5" width="16" height="3" rx="1.5" fill="#fff" />
            <rect x="8" y="17" width="10" height="3" rx="1.5" fill="#fff" />
        </svg>
    );
}
