"""Remote ZIP directory parser tests use tiny synthetic transport fixtures only."""
import io
import struct
import unittest
import zipfile
from fetch_architecture_sources import central_directory


def directory(name):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name,b'transport fixture, not IFC experiment data')
    data=stream.getvalue()
    end=data.rfind(b'PK\x05\x06')
    header=struct.unpack_from('<4s4H2IH',data,end)
    return data[header[6]:header[6]+header[5]]


class RemoteZIPTests(unittest.TestCase):
    def test_read_real_zipfile_directory_layout(self):
        rows=central_directory(directory('ARCH/IFC/office.ifc'))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['name'],'ARCH/IFC/office.ifc')
        self.assertEqual(rows[0]['method'],8)
        self.assertGreater(rows[0]['compressed_size'],0)

    def test_traversal_rejected(self):
        with self.assertRaises(ValueError):
            central_directory(directory('../office.ifc'))

    def test_invalid_signature_rejected(self):
        with self.assertRaises(ValueError):
            central_directory(b'not a zip directory')


if __name__=='__main__':
    unittest.main()
