import ApplicationLogo from '@/Components/ApplicationLogo';
import CuratorStatusModal from '@/Components/CuratorStatusModal';
import { ToastProvider } from '@/providers/ToastProvider';
import { useAuthRole } from '@/Hooks/useAuthRole';
import { Link, usePage } from '@inertiajs/react';
import DashboardRoundedIcon from '@mui/icons-material/DashboardRounded';
import FactCheckRoundedIcon from '@mui/icons-material/FactCheckRounded';
import GroupRoundedIcon from '@mui/icons-material/GroupRounded';
import HistoryRoundedIcon from '@mui/icons-material/HistoryRounded';
import KeyRoundedIcon from '@mui/icons-material/KeyRounded';
import InsightsRoundedIcon from '@mui/icons-material/InsightsRounded';
import MemoryRoundedIcon from '@mui/icons-material/MemoryRounded';
import PrecisionManufacturingRoundedIcon from '@mui/icons-material/PrecisionManufacturingRounded';
import MonitorHeartRoundedIcon from '@mui/icons-material/MonitorHeartRounded';
import NotificationsRoundedIcon from '@mui/icons-material/NotificationsRounded';
import MenuRoundedIcon from '@mui/icons-material/MenuRounded';
import RateReviewRoundedIcon from '@mui/icons-material/RateReviewRounded';
import BoltRoundedIcon from '@mui/icons-material/BoltRounded';
import TimelineRoundedIcon from '@mui/icons-material/TimelineRounded';
import NewspaperRoundedIcon from '@mui/icons-material/NewspaperRounded';
import PersonRoundedIcon from '@mui/icons-material/PersonRounded';
import PlayCircleOutlineRoundedIcon from '@mui/icons-material/PlayCircleOutlineRounded';
import TuneRoundedIcon from '@mui/icons-material/TuneRounded';
import {
    AppBar,
    Avatar,
    Badge,
    Box,
    Button,
    Chip,
    Divider,
    Drawer,
    IconButton,
    List,
    ListItemButton,
    ListItemIcon,
    ListItemText,
    Stack,
    Toolbar,
    Tooltip,
    Typography,
} from '@mui/material';
import { useMemo, useState } from 'react';

const drawerWidth = 272;

const navigationItems = [
    {
        label: 'Dashboard',
        routeName: 'dashboard',
        match: 'dashboard',
        icon: DashboardRoundedIcon,
    },
    {
        label: 'Outlets',
        routeName: 'outlets.index',
        match: 'outlets.*',
        icon: NewspaperRoundedIcon,
    },
    {
        label: 'Scraping',
        routeName: 'scraping.index',
        match: 'scraping.*',
        icon: PlayCircleOutlineRoundedIcon,
    },
    {
        label: 'Run History',
        routeName: 'run-history.index',
        match: 'run-history.*',
        icon: TimelineRoundedIcon,
    },
    {
        label: 'Scrape Results',
        routeName: 'scrape-results.index',
        match: 'scrape-results.*',
        icon: FactCheckRoundedIcon,
    },
    {
        label: 'Runtime',
        routeName: 'runtime.index',
        match: 'runtime.*',
        icon: MemoryRoundedIcon,
    },
    {
        label: 'System Health',
        routeName: 'health.index',
        match: 'health.*',
        icon: MonitorHeartRoundedIcon,
    },
    {
        label: 'Alerts',
        routeName: 'alerts.index',
        match: 'alerts.*',
        icon: NotificationsRoundedIcon,
    },
    {
        label: 'Curator Settings',
        routeName: 'settings.edit',
        match: 'settings.*',
        icon: TuneRoundedIcon,
        requires: 'admin',
    },
    {
        label: 'Moderation',
        routeName: 'moderation.index',
        match: 'moderation.*',
        icon: RateReviewRoundedIcon,
    },
    {
        label: 'Breaking Desk',
        routeName: 'breaking.index',
        match: 'breaking.*',
        icon: BoltRoundedIcon,
    },
    {
        label: 'Cost & Usage',
        routeName: 'model-usage.index',
        match: 'model-usage.*',
        icon: InsightsRoundedIcon,
    },
    {
        label: 'API Keys',
        routeName: 'api-keys.index',
        match: 'api-keys.*',
        icon: KeyRoundedIcon,
        requires: 'admin',
    },
    {
        label: 'Audit Log',
        routeName: 'audit-log.index',
        match: 'audit-log.*',
        icon: HistoryRoundedIcon,
        requires: 'admin',
    },
    {
        label: 'Users',
        routeName: 'users.index',
        match: 'users.*',
        icon: GroupRoundedIcon,
        requires: 'admin',
    },
    {
        label: 'Profile',
        routeName: 'profile.edit',
        match: 'profile.*',
        icon: PersonRoundedIcon,
    },
];

// Whether a nav item is visible for the given role gates.
const navItemVisible = (item, gates) => {
    if (item.requires === 'admin') {
        return gates.isAdmin;
    }
    if (item.requires === 'operator') {
        return gates.isOperator;
    }

    return true;
};

const roleLabel = (role) => {
    if (!role) {
        return null;
    }

    return role.charAt(0).toUpperCase() + role.slice(1);
};

const getUserInitials = (name) => {
    if (!name) {
        return 'U';
    }

    return name
        .split(' ')
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part.charAt(0).toUpperCase())
        .join('');
};

export default function AppLayout({
    title = 'Platform',
    subtitle = '',
    children,
}) {
    const { auth, alerts } = usePage().props;
    const gates = useAuthRole();
    const [mobileOpen, setMobileOpen]           = useState(false);
    const [curatorModalOpen, setCuratorModalOpen] = useState(false);
    const user = auth?.user;
    const openAlertCount = alerts?.open_count ?? 0;

    const userInitials = useMemo(() => getUserInitials(user?.name), [user]);
    const visibleNavItems = useMemo(
        () => navigationItems.filter((item) => navItemVisible(item, gates)),
        [gates],
    );

    const drawer = (
        <Box sx={{ height: '100%', backgroundColor: 'background.paper' }}>
            <Stack
                direction="row"
                alignItems="center"
                spacing={1.5}
                sx={{ px: 2.5, py: 2 }}
            >
                <ApplicationLogo style={{ height: 28, width: 28, fill: '#0f5fd7' }} />
                <Box>
                    <Typography variant="subtitle2" fontWeight={700}>
                        Messor
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                        InkBytes Backoffice
                    </Typography>
                </Box>
            </Stack>

            <Divider />

            <List sx={{ px: 1.25, py: 1.5 }}>
                {visibleNavItems.map((item) => {
                    const Icon = item.icon;
                    const selected = route().current(item.match);

                    return (
                        <ListItemButton
                            key={item.routeName}
                            component={Link}
                            href={route(item.routeName)}
                            selected={selected}
                            onClick={() => setMobileOpen(false)}
                            sx={{
                                borderRadius: 2,
                                mb: 0.5,
                            }}
                        >
                            <ListItemIcon sx={{ minWidth: 36 }}>
                                <Icon fontSize="small" />
                            </ListItemIcon>
                            <ListItemText primary={item.label} />
                        </ListItemButton>
                    );
                })}
            </List>
        </Box>
    );

    return (
        <ToastProvider>
            <Box sx={{ display: 'flex', minHeight: '100vh' }}>
            <AppBar
                position="fixed"
                color="inherit"
                elevation={0}
                sx={{
                    width: { lg: `calc(100% - ${drawerWidth}px)` },
                    ml: { lg: `${drawerWidth}px` },
                    borderBottom: '1px solid',
                    borderColor: 'divider',
                    backgroundColor: 'background.paper',
                }}
            >
                <Toolbar sx={{ minHeight: '72px !important', px: { xs: 2, sm: 3 } }}>
                    <IconButton
                        color="inherit"
                        edge="start"
                        onClick={() => setMobileOpen((value) => !value)}
                        sx={{ mr: 1, display: { lg: 'none' } }}
                    >
                        <MenuRoundedIcon />
                    </IconButton>

                    <Box sx={{ flexGrow: 1 }} />

                    <Stack direction="row" alignItems="center" spacing={1.25}>
                        {/* Curator live-status modal trigger */}
                        <Tooltip title="Curator pipeline status">
                            <IconButton
                                color="inherit"
                                onClick={() => setCuratorModalOpen(true)}
                                aria-label="curator status"
                            >
                                <PrecisionManufacturingRoundedIcon />
                            </IconButton>
                        </Tooltip>

                        <Tooltip
                            title={
                                openAlertCount > 0
                                    ? `${openAlertCount} open alert(s)`
                                    : 'No open alerts'
                            }
                        >
                            <IconButton
                                color="inherit"
                                component={Link}
                                href={route('alerts.index')}
                                aria-label="alerts"
                            >
                                <Badge
                                    badgeContent={openAlertCount}
                                    color="error"
                                    overlap="circular"
                                >
                                    <NotificationsRoundedIcon />
                                </Badge>
                            </IconButton>
                        </Tooltip>

                        <Avatar
                            sx={{
                                width: 34,
                                height: 34,
                                bgcolor: 'primary.main',
                                color: 'primary.contrastText',
                                fontSize: 13,
                                fontWeight: 700,
                            }}
                        >
                            {userInitials}
                        </Avatar>

                        <Box sx={{ display: { xs: 'none', sm: 'block' } }}>
                            <Typography variant="body2" fontWeight={600}>
                                {user?.name ?? 'Unknown User'}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                {user?.email ?? ''}
                            </Typography>
                        </Box>

                        {gates.role ? (
                            <Chip
                                size="small"
                                label={roleLabel(gates.role)}
                                color={gates.isAdmin ? 'primary' : 'default'}
                                variant={gates.isAdmin ? 'filled' : 'outlined'}
                                sx={{ display: { xs: 'none', sm: 'inline-flex' } }}
                            />
                        ) : null}

                        <Button
                            size="small"
                            variant="outlined"
                            component={Link}
                            href={route('logout')}
                            method="post"
                        >
                            Log Out
                        </Button>
                    </Stack>
                </Toolbar>
            </AppBar>

            <Box
                component="nav"
                sx={{ width: { lg: drawerWidth }, flexShrink: { lg: 0 } }}
            >
                <Drawer
                    variant="temporary"
                    open={mobileOpen}
                    onClose={() => setMobileOpen(false)}
                    ModalProps={{ keepMounted: true }}
                    sx={{
                        display: { xs: 'block', lg: 'none' },
                        '& .MuiDrawer-paper': {
                            boxSizing: 'border-box',
                            width: drawerWidth,
                        },
                    }}
                >
                    {drawer}
                </Drawer>

                <Drawer
                    variant="permanent"
                    open
                    sx={{
                        display: { xs: 'none', lg: 'block' },
                        '& .MuiDrawer-paper': {
                            boxSizing: 'border-box',
                            width: drawerWidth,
                            borderRight: '1px solid',
                            borderColor: 'divider',
                        },
                    }}
                >
                    {drawer}
                </Drawer>
            </Box>

            <Box
                component="main"
                sx={{
                    flexGrow: 1,
                    width: { lg: `calc(100% - ${drawerWidth}px)` },
                    ml: { lg: `${drawerWidth}px` },
                    mt: '72px',
                    px: { xs: 2, sm: 3, md: 4 },
                    py: { xs: 2.5, sm: 3 },
                }}
            >
                <Box sx={{ mx: 'auto', maxWidth: 1200 }}>
                    <Typography variant="h4">{title}</Typography>
                    {subtitle ? (
                        <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{ mt: 0.75 }}
                        >
                            {subtitle}
                        </Typography>
                    ) : null}
                    <Box sx={{ mt: 3 }}>{children}</Box>
                </Box>
            </Box>
            </Box>

            {/* Curator pipeline status modal — triggered by the ⚙ icon in the header */}
            <CuratorStatusModal
                open={curatorModalOpen}
                onClose={() => setCuratorModalOpen(false)}
            />
        </ToastProvider>
    );
}
