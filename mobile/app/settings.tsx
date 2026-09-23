import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Alert } from 'react-native';
import { useRouter } from 'expo-router';

import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { Container } from '@/components/ui/Container';
import { HStack } from '@/components/ui/HStack';
import { Input } from '@/components/ui/Input';
import { Section } from '@/components/ui/Section';
import { Text } from '@/components/ui/Text';
import { VStack } from '@/components/ui/VStack';
import { fetchInstitutionalSettings, updateInstitutionalSettings } from '@/lib/api';
import type { InstitutionalSettings } from '@/lib/api';

export default function SettingsScreen() {
  const router = useRouter();
  const [settings, setSettings] = useState<InstitutionalSettings | null>(null);
  const [organization, setOrganization] = useState('');
  const [maxTrade, setMaxTrade] = useState('1000');
  const [adminIds, setAdminIds] = useState('');
  const [botToken, setBotToken] = useState('');
  const [polymarketKey, setPolymarketKey] = useState('');
  const [polymarketSecret, setPolymarketSecret] = useState('');
  const [polymarketPassphrase, setPolymarketPassphrase] = useState('');
  const [walletKey, setWalletKey] = useState('');
  const [securityPin, setSecurityPin] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const value = await fetchInstitutionalSettings();
      setSettings(value);
      setOrganization(value.organization_name);
      setMaxTrade(String(value.max_trade_amount));
      setAdminIds(value.authorized_admin_telegram_ids.join(', '));
    } catch {
      Alert.alert('Settings unavailable', 'We could not load the institutional settings.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const save = async () => {
    if (!settings) return;
    setSaving(true);
    try {
      const updated = await updateInstitutionalSettings({
        organization_name: organization.trim(),
        execution_mode: settings.execution_mode,
        risk_preset: settings.risk_preset,
        max_trade_amount: Number(maxTrade),
        authorized_admin_telegram_ids: adminIds.split(',').map((value) => value.trim()).filter(Boolean),
        ...(botToken ? { telegram_bot_token: botToken } : {}),
        ...(polymarketKey ? { polymarket_api_key: polymarketKey } : {}),
        ...(polymarketSecret ? { polymarket_api_secret: polymarketSecret } : {}),
        ...(polymarketPassphrase ? { polymarket_passphrase: polymarketPassphrase } : {}),
        ...(walletKey ? { wallet_private_key: walletKey } : {}),
        ...(securityPin ? { admin_security_pin: securityPin } : {}),
      }, adminIds.split(',').map((value) => value.trim()).find(Boolean));
      setSettings(updated);
      setBotToken(''); setPolymarketKey(''); setPolymarketSecret(''); setPolymarketPassphrase(''); setWalletKey(''); setSecurityPin('');
      Alert.alert('Settings saved', 'Your institutional controls have been updated.');
    } catch {
      Alert.alert('Could not save', 'Please check the fields and try again.');
    } finally {
      setSaving(false);
    }
  };

  if (loading || !settings) {
    return <Container><ActivityIndicator color="#007AFF" /></Container>;
  }

  return (
    <Container keyboard>
      <VStack gap="lg">
        <Section title="Admin settings" subtitle="Configure Telegram access, execution mode, and risk controls."><Text /></Section>
        <Card><CardContent className="gap-3 p-4">
          <Text className="font-semibold">Workspace</Text>
          <Input value={organization} onChangeText={setOrganization} placeholder="Organization name" placeholderTextColor="#8E8E93" />
          <HStack gap="sm"><Chip selected={settings.execution_mode === 'paper'} onPress={() => setSettings({ ...settings, execution_mode: 'paper' })}>Paper</Chip><Chip selected={settings.execution_mode === 'live'} onPress={() => setSettings({ ...settings, execution_mode: 'live' })}>Live</Chip></HStack>
          <Text className="text-sm text-text-secondary">Live mode submits guarded limit orders to Polymarket. Paper mode records the full decision without sending an order.</Text>
        </CardContent></Card>
        <Card><CardContent className="gap-3 p-4">
          <Text className="font-semibold">Risk preset</Text>
          <HStack gap="sm"><Chip selected={settings.risk_preset === 'conservative'} onPress={() => setSettings({ ...settings, risk_preset: 'conservative' })}>🛡️ Conservative</Chip><Chip selected={settings.risk_preset === 'balanced'} onPress={() => setSettings({ ...settings, risk_preset: 'balanced' })}>⚖️ Balanced</Chip><Chip selected={settings.risk_preset === 'aggressive'} onPress={() => setSettings({ ...settings, risk_preset: 'aggressive' })}>🚀 Aggressive</Chip></HStack>
          <Input value={maxTrade} onChangeText={setMaxTrade} keyboardType="decimal-pad" placeholder="Maximum trade amount" placeholderTextColor="#8E8E93" />
          <Text className="text-sm text-text-secondary">Every order still requires more than 3% expected value, at least 75% confidence, and enough live liquidity.</Text>
        </CardContent></Card>
        <Card><CardContent className="gap-3 p-4">
          <Text className="font-semibold">Telegram access</Text>
          <Input value={adminIds} onChangeText={setAdminIds} placeholder="Authorized Telegram IDs, comma separated" placeholderTextColor="#8E8E93" keyboardType="numbers-and-punctuation" />
          <Input value={botToken} onChangeText={setBotToken} placeholder={settings.has_telegram_bot_token ? 'Bot token saved — enter to replace' : 'Telegram bot token'} placeholderTextColor="#8E8E93" secureTextEntry />
          <Text className="text-sm text-text-secondary">Everyone can ask informational questions. Only these IDs receive trade buttons and can authorize execution.</Text>
        </CardContent></Card>
        <Card><CardContent className="gap-3 p-4">
          <Text className="font-semibold">Polymarket credentials</Text>
          <Input value={polymarketKey} onChangeText={setPolymarketKey} placeholder={settings.has_polymarket_credentials ? 'API key saved — enter to replace' : 'API key'} placeholderTextColor="#8E8E93" secureTextEntry />
          <Input value={polymarketSecret} onChangeText={setPolymarketSecret} placeholder="API secret" placeholderTextColor="#8E8E93" secureTextEntry />
          <Input value={polymarketPassphrase} onChangeText={setPolymarketPassphrase} placeholder="API passphrase" placeholderTextColor="#8E8E93" secureTextEntry />
          <Input value={walletKey} onChangeText={setWalletKey} placeholder={settings.has_wallet_private_key ? 'Wallet key saved — enter to replace' : 'Wallet private key'} placeholderTextColor="#8E8E93" secureTextEntry />
          <Input value={securityPin} onChangeText={setSecurityPin} placeholder={settings.has_admin_security_pin ? 'Security PIN saved — enter to replace' : 'Admin security PIN'} placeholderTextColor="#8E8E93" secureTextEntry keyboardType="number-pad" />
        </CardContent></Card>
        <Button size="lg" onPress={() => void save()} disabled={saving}>{saving ? 'Saving…' : 'Save settings'}</Button>
        <Button variant="secondary" onPress={() => router.push('/trades')}>View trade history</Button>
      </VStack>
    </Container>
  );
}
