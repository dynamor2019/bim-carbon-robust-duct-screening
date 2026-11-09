"""Tree arithmetic fixtures only; not reconstructed IFC service networks."""
import copy
import math
import unittest
from candidate_tree_flow import validate_tree


def fixture():
    nodes=['t1','t2','b','r']
    demands={'t1':.1,'t2':.2}
    edges=[{'id':eid,'from':a,'to':b,'length_m':length,'diameter_m':.5,'spatial_authorized':True,
        'connection_authorized':True,'authorization_ref':'SOFTWARE_FIXTURE_ONLY'} for eid,a,b,length in [('e1','t1','b',2),('e2','t2','b',3),('e3','b','r',4)]]
    return nodes,edges,demands


class CandidateTreeTests(unittest.TestCase):
    def test_merge_and_analytical_velocity(self):
        nodes,edges,demands=fixture()
        result=validate_tree(nodes,edges,'r',demands,10.)
        flows={r['edge_id']:r for r in result['edges']}
        self.assertAlmostEqual(flows['e3']['flow_m3_s'],.3)
        self.assertAlmostEqual(flows['e3']['velocity_m_s'],.3/(math.pi*.5**2/4))
        self.assertEqual(result['terminal_paths']['t1'],['e1','e3'])
        self.assertTrue(all(abs(r['residual_m3_s'])<1e-12 for r in result['node_conservation']))
        self.assertFalse(result['pressure_balance_checked'])

    def test_undersized_design_is_retained_as_failure(self):
        nodes,edges,demands=fixture()
        edges[-1]['diameter_m']=.01
        result=validate_tree(nodes,edges,'r',demands,5.)
        self.assertEqual(result['status'],'FAIL_VELOCITY_LIMIT')
        self.assertEqual(len(result['edges']),3)

    def test_cycles_disconnect_and_split_rejected(self):
        nodes,edges,demands=fixture()
        bad=copy.deepcopy(edges)
        bad[-1]['to']='t1'
        with self.assertRaises(ValueError):
            validate_tree(nodes,bad,'r',demands,10.)
        with self.assertRaises(ValueError):
            validate_tree(nodes,edges[:-1],'r',demands,10.)
        with self.assertRaises(ValueError):
            validate_tree(nodes,edges+[dict(edges[0],id='extra',to='r')],'r',demands,10.)

    def test_unknown_leaves_and_internal_terminals_rejected(self):
        nodes,edges,demands=fixture()
        for bad in ({'t1':.1},{'t1':.1,'t2':.2,'b':.1}):
            with self.assertRaises(ValueError):
                validate_tree(nodes,edges,'r',bad,10.)

    def test_unapproved_contacts_and_missing_refs_rejected(self):
        nodes,edges,demands=fixture()
        for key,value in [('connection_authorized',False),('spatial_authorized',None),('authorization_ref','')]:
            bad=copy.deepcopy(edges)
            bad[0][key]=value
            with self.assertRaises(ValueError):
                validate_tree(nodes,bad,'r',demands,10.)

    def test_zero_flow_kept_and_negative_nan_rejected(self):
        nodes,edges,demands=fixture()
        demands['t1']=0.
        result=validate_tree(nodes,edges,'r',demands,10.)
        self.assertEqual(result['edges'][0]['flow_m3_s'],0.)
        for q in (-.1,float('nan'),True):
            with self.assertRaises(ValueError):
                validate_tree(nodes,edges,'r',dict(demands,t1=q),10.)

    def test_independent_terminal_path_accumulation(self):
        nodes,edges,demands=fixture()
        result=validate_tree(nodes,edges,'r',demands,10.)
        # Explicit independent path incidence, not the module's parent traversal.
        incidence={'e1':('t1',),'e2':('t2',),'e3':('t1','t2')}
        expected={eid:sum(demands[t] for t in terms) for eid,terms in incidence.items()}
        for row in result['edges']:
            self.assertAlmostEqual(row['flow_m3_s'],expected[row['edge_id']])


if __name__=='__main__':
    unittest.main()
