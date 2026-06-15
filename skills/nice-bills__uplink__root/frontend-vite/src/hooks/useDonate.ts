/**
 * useDonate Hook
 * Handles on-chain donation transactions via wagmi
 * Calls contract functions directly to ensure proper tracking
 */

import { useState, useCallback } from 'react';
import { useAccount, useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import { parseEther } from 'viem';
import { createDonation } from '../lib/api';
import type { TokenType } from '../types';

// CampaignFactory ABI - only the contribute function we need
const CAMPAIGN_FACTORY_ABI = [
  {
    inputs: [{ name: '_campaignId', type: 'uint256' }],
    name: 'contribute',
    outputs: [],
    stateMutability: 'payable',
    type: 'function',
  },
] as const;

interface UseDonateOptions {
    campaignId: string;
    onSuccess?: (txHash: string) => void;
    onError?: (error: Error) => void;
}

interface UseDonateReturn {
    donate: (amount: number) => Promise<void>;
    isLoading: boolean;
    isPending: boolean;
    isSuccess: boolean;
    error: Error | null;
    txHash: string | null;
}

export function useDonate({ campaignId, onSuccess, onError }: UseDonateOptions): UseDonateReturn {
    const { address, isConnected } = useAccount();
    const [error, setError] = useState<Error | null>(null);
    const [txHash, setTxHash] = useState<string | null>(null);

    const { writeContractAsync, isPending } = useWriteContract();

    const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
        hash: txHash as `0x${string}` | undefined,
    });

    const donate = useCallback(async (amount: number) => {
        if (!isConnected || !address) {
            const err = new Error('Wallet not connected');
            setError(err);
            onError?.(err);
            return;
        }

        if (amount <= 0) {
            const err = new Error('Amount must be greater than 0');
            setError(err);
            onError?.(err);
            return;
        }

        try {
            setError(null);

            const factoryAddress = import.meta.env.VITE_CAMPAIGN_FACTORY;
            if (!factoryAddress) {
                throw new Error('Campaign factory address not configured');
            }

            // Call contribute function on CampaignFactory
            // This properly tracks which campaign the donation belongs to
            const hash = await writeContractAsync({
                address: factoryAddress as `0x${string}`,
                abi: CAMPAIGN_FACTORY_ABI,
                functionName: 'contribute',
                args: [BigInt(campaignId)],
                value: parseEther(amount.toString()),
            });

            setTxHash(hash);

            // Record donation in backend
            await createDonation(campaignId, {
                donor_address: address,
                amount,
                token_type: 'MON' as TokenType,
                tx_hash: hash,
            });

            onSuccess?.(hash);
        } catch (err) {
            const error = err instanceof Error ? err : new Error('Transaction failed');
            setError(error);
            onError?.(error);
        }
    }, [isConnected, address, campaignId, writeContractAsync, onSuccess, onError]);

    return {
        donate,
        isLoading: isPending || isConfirming,
        isPending,
        isSuccess,
        error,
        txHash,
    };
}
