import AppLayout from '@/Layouts/AppLayout';

const extractHeaderTitle = (header) => {
    if (!header) {
        return 'Workspace';
    }

    if (typeof header === 'string') {
        return header;
    }

    const headerChildren = header?.props?.children;

    if (typeof headerChildren === 'string') {
        return headerChildren;
    }

    return 'Workspace';
};

export default function AuthenticatedLayout({ header, children }) {
    return <AppLayout title={extractHeaderTitle(header)}>{children}</AppLayout>;
}
